from django import forms
from .models import Player, User
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "id": "email-field",
                "class": "form-control border-start-0 fs-6 bg-light",
                "placeholder": "name@example.com",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "username" in self.fields:
            self.fields["username"].widget.attrs.update(
                {
                    "id": "username-field",
                    "class": "form-control border-start-0 fs-6 bg-light",
                    "placeholder": "Choose a username",
                    "autofocus": True,
                }
            )

        if "password1" in self.fields:
            self.fields["password1"].widget.attrs.update(
                {
                    "id": "password-field",
                    "class": "form-control border-start-0 fs-6 bg-light",
                    "placeholder": "••••••••",
                }
            )
        if "password2" in self.fields:
            self.fields["password2"].label = "Confirm Password"
            self.fields["password2"].widget.attrs.update(
                {
                    "id": "confirmation-field",
                    "class": "form-control border-start-0 fs-6 bg-light",
                    "placeholder": "Repeat your password",
                }
            )


class PlayerRegistrationForm(forms.ModelForm):
    nickname = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "id": "id_nickname",
                "class": "form-control border-start-0 fs-6 bg-light",
                "placeholder": "Enter your nickname",
                "autofocus": True,
            }
        )
    )


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "id": "id_username",
                "class": "form-control border-start-0 fs-6 bg-light",
                "placeholder": "Enter your username",
                "autofocus": True,
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "id": "id_password",
                "class": "form-control border-start-0 fs-6 bg-light",
                "placeholder": "••••••••",
            }
        )
    )


class GuestForm(forms.ModelForm):
    selected_preset = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Player
        fields = ["nickname"]

        widgets = {
            "nickname": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your custom nickname...",
                    "maxlength": "16",
                }
            ),
        }

    def clean_nickname(self):
        nickname: str = self.cleaned_data.get("nickname")
        if not nickname or len(nickname.strip()) < 3:
            raise forms.ValidationError(
                "Your nickname must be at least 3 characters long."
            )
        return nickname


class EditPlayerForm(forms.ModelForm):
    selected_preset = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Player
        fields = ["nickname", "avatar"]
        widgets = {
            "nickname": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your custom nickname...",
                    "maxlength": "16",
                }
            ),
            "avatar": forms.FileInput(
                attrs={"class": "d-none", "accept": "image/png, image/jpeg, image/jpg"}
            ),
        }

    def clean_nickname(self):
        nickname: str = self.cleaned_data.get("nickname")

        if not nickname or len(nickname.strip()) < 3:
            raise forms.ValidationError(
                "Your nickname must be at least 3 characters long."
            )

        return nickname.strip()
