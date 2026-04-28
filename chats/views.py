from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Max
from .models import Chat, ChatMessage
from clients.models import ClientProfile
from masters.models import MasterProfile
from django.utils import timezone


@login_required
def chats_list(request):
    if request.user.role == 'client':
        client = get_object_or_404(ClientProfile, user=request.user)
        chats = Chat.objects.filter(client=client).select_related(
            'master', 'master__user'
        ).annotate(last_message_time=Max('messages__created_at')).order_by('-created_at')

    elif request.user.role == 'master':
        master = get_object_or_404(MasterProfile, user=request.user)
        chats = Chat.objects.filter(master=master).select_related(
            'client', 'client__user'
        ).annotate(last_message_time=Max('messages__created_at')).order_by('-created_at')

    else:
        messages.error(request, 'У вас нет доступа')
        return redirect('home')

    chats_data = []

    for chat in chats:
        last_message = chat.last_message or chat.messages.order_by(
            '-created_at').first()

        unread_count = ChatMessage.objects.filter(
            chat=chat,
            is_read=False
        ).exclude(sender=request.user).count()

        chats_data.append({
            'chat': chat,
            'last_message': last_message,
            'unread_count': unread_count,
        })

    return render(request, 'chats/chats_list.html', {
        'chats_data': chats_data
    })


@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)

    # Проверка доступа
    if request.user.role == 'client' and chat.client.user != request.user:
        messages.error(request, 'У вас нет доступа к этому чату')
        return redirect('chats_list')

    if request.user.role == 'master' and chat.master.user != request.user:
        messages.error(request, 'У вас нет доступа к этому чату')
        return redirect('chats_list')

    # Отметка сообщений как прочитанных
    ChatMessage.objects.filter(
        chat=chat,
        is_read=False
    ).exclude(sender=request.user).update(
        is_read=True,
        read_at=timezone.now()
    )

    # === ОТПРАВКА СООБЩЕНИЯ / ФАЙЛА ===
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        attachment = request.FILES.get('attachment')
        reply_to_id = request.POST.get('reply_to_id')

        reply_to = None
        if reply_to_id:
            reply_to = ChatMessage.objects.filter(
                id=reply_to_id,
                chat=chat
            ).first()

        if content or attachment:
            message = ChatMessage.objects.create(
                chat=chat,
                sender=request.user,
                content=content,
                attachment=attachment,
                reply_to=reply_to
            )

            chat.last_message = message
            chat.save(update_fields=['last_message'])

        return redirect('chat_detail', chat_id=chat.id)

    # === ПОЛУЧЕНИЕ СООБЩЕНИЙ ===
    messages_qs = chat.messages.select_related(
        'sender', 'reply_to', 'reply_to__sender').order_by('created_at')

    visible_messages = []

    for msg in messages_qs:
        if msg.deleted_for_all:
            continue

        if msg.sender == request.user and msg.deleted_for_sender:
            continue

        if msg.sender != request.user and msg.deleted_for_receiver:
            continue

        visible_messages.append(msg)

    # === ГРУППИРОВКА ПО ДАТАМ ===
    grouped_messages = []
    current_date = None

    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    today = timezone.localdate()

    for msg in visible_messages:
        msg_date = msg.created_at.date()

        if msg_date == today:
            date_label = 'Сегодня'
        elif msg_date == today - timezone.timedelta(days=1):
            date_label = 'Вчера'
        else:
            date_label = f'{msg_date.day} {months[msg_date.month]} {msg_date.year}'

        if current_date != msg_date:
            grouped_messages.append({
                'date_label': date_label,
                'messages': []
            })
            current_date = msg_date

        grouped_messages[-1]['messages'].append(msg)

    return render(request, 'chats/chat_detail.html', {
        'chat': chat,
        'grouped_messages': grouped_messages,
    })


@login_required
def start_chat_with_master(request, master_id):
    if request.user.role != 'client':
        messages.error(request, 'Чат с мастером доступен только клиенту')
        return redirect('home')

    client = get_object_or_404(ClientProfile, user=request.user)
    master = get_object_or_404(MasterProfile, id=master_id)

    chat, created = Chat.objects.get_or_create(
        client=client,
        master=master
    )

    return redirect('chat_detail', chat_id=chat.id)


@login_required
def start_chat_with_client(request, client_id):
    if request.user.role != 'master':
        messages.error(request, 'Чат с клиентом доступен только мастеру')
        return redirect('home')

    master = get_object_or_404(MasterProfile, user=request.user)
    client = get_object_or_404(ClientProfile, id=client_id)

    chat, created = Chat.objects.get_or_create(
        client=client,
        master=master
    )

    return redirect('chat_detail', chat_id=chat.id)


def format_chat_date(value):
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    today = timezone.localdate()
    message_date = value.date()

    if message_date == today:
        return 'Сегодня'

    if message_date == today - timezone.timedelta(days=1):
        return 'Вчера'

    return f'{message_date.day} {months[message_date.month]} {message_date.year}'


@login_required
def delete_message(request, message_id):
    message = get_object_or_404(ChatMessage, id=message_id)
    chat = message.chat

    if request.user.role == 'client' and chat.client.user != request.user:
        messages.error(request, 'Нет доступа')
        return redirect('chats_list')

    if request.user.role == 'master' and chat.master.user != request.user:
        messages.error(request, 'Нет доступа')
        return redirect('chats_list')

    if request.method == 'POST':
        delete_type = request.POST.get('delete_type')

        if delete_type == 'all':
            if message.sender != request.user:
                messages.error(
                    request, 'Удалить для всех можно только своё сообщение')
                return redirect('chat_detail', chat_id=chat.id)

            message.deleted_for_all = True

        else:
            if message.sender == request.user:
                message.deleted_for_sender = True
            else:
                message.deleted_for_receiver = True

        message.save()

    return redirect('chat_detail', chat_id=chat.id)


@login_required
def edit_message(request, message_id):
    message = get_object_or_404(ChatMessage, id=message_id)
    chat = message.chat

    if message.sender != request.user:
        messages.error(request, 'Редактировать можно только своё сообщение')
        return redirect('chat_detail', chat_id=chat.id)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()

        if content:
            message.content = content
            message.edited_at = timezone.now()
            message.save(update_fields=['content', 'edited_at'])

    return redirect('chat_detail', chat_id=chat.id)
