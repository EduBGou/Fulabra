from django import forms
from .models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nickname', 'avatar']
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Escolhe seu novo apelido'
            }),
            'avatar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'avatar.png'
            }), # Futuramente se migrar para um upload de arquivos -> forms.FileInput
        }
        