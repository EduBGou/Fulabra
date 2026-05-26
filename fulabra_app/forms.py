from django import forms
from .models import User

class UserProfileForm(forms.ModelForm):
    selected_preset = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['nickname', 'avatar']
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Escolhe seu novo apelido'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'd-none',
                'accept': 'image/png, image/jpeg, image/jpg'
            }),
        }
    
    def clean_nickname(self):
        nickname = self.cleaned_data.get('nickname')

        if not nickname or len(nickname.strip()) == 0:
            raise forms.ValidationError("Escolha um apelido válido.")
        
        return nickname.strip()