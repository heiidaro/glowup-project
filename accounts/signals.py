from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from masters.models import MasterProfile
from clients.models import ClientProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.role == "master":
        MasterProfile.objects.create(user=instance, display_name="Новый мастер", address_text="")  # минимум
    elif instance.role == "client":
        ClientProfile.objects.create(user=instance)
