from django import forms
from .models import Game, GameRound, Player, SubmittedWord, User, Word
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
                    "placeholder": "Enter your password",
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
                "placeholder": "Enter your password",
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


class EditPlayerForm(GuestForm):
    class Meta:
        model = Player
        fields = fields = GuestForm.Meta.fields + ["avatar"]
        widgets = {
            **GuestForm.Meta.widgets,
            "avatar": forms.FileInput(
                attrs={"class": "d-none", "accept": "image/png, image/jpeg, image/jpg"}
            ),
        }


class GameWordForm(forms.Form):
    action = forms.CharField(
        widget=forms.HiddenInput(attrs={"id": "action"}), initial="submit_word"
    )

    word = forms.CharField(
        max_length=40,
        widget=forms.TextInput(
            attrs={
                "id": "word-input",
                "class": "form-control form-control-lg fw-semibold",
                "placeholder": "Type to search...",
                "list": "word-list",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.current_round: GameRound = kwargs.pop("round", None)
        super().__init__(*args, **kwargs)

    def clean_word(self):
        word_label: str = self.cleaned_data.get("word")
        word_obj = Word.objects.filter(label=word_label).first()

        if not word_obj:
            raise forms.ValidationError("This word is not in the game dictionary!")

        if word_obj.category != self.current_round.game.category:
            raise forms.ValidationError("This word don't belong to this category!")

        if self.current_round.game and self.current_round:
            word_already_used = SubmittedWord.objects.filter(
                round__game=self.current_round.game,
                round__round_number__lt=self.current_round.round_number,
                word=word_obj,
            ).exists()

            if word_already_used:
                raise forms.ValidationError("This word was already used!")

        return word_obj
