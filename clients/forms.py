from django import forms
from .models import ClientPost, ServiceTag


class ClientPostForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=ServiceTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Теги"
    )

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
