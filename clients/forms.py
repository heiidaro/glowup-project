from django import forms
from .models import ClientPost, ServiceTag
from masters.models import ServiceCategory


class ClientPostForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'tags' not in self.fields:
            return

        category_names = list(
            ServiceCategory.objects
            .exclude(name__isnull=True)
            .exclude(name='')
            .values_list('name', flat=True)
            .order_by('name')
        )

        category_names = [name.strip()
                          for name in category_names if name and name.strip()]

        tag_field = self.fields['tags']

        if hasattr(tag_field, 'queryset'):
            TagModel = tag_field.queryset.model

            for name in category_names:
                TagModel.objects.get_or_create(name=name)

            tag_field.queryset = TagModel.objects.filter(
                name__in=category_names
            ).order_by('name')

    class Meta:
        model = ClientPost
        fields = ['description', 'tags', 'preferred_date',
                  'preferred_time', 'budget', 'image', 'is_anonymous']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Опишите, что вы ищете...'}),
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
            'budget': forms.NumberInput(attrs={'placeholder': 'Ваш бюджет в рублях'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
