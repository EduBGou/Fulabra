from django.db.models import Q

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

from .utils import hx_redirect
from .forms import LoginForm, PlayerRegistrationForm, UserProfileForm
from .models import *


def index_view(request: HttpRequest):
    return render(request, "fulabra_app/index.html")


def handle_lobby_view(request: HttpRequest):
    lobby_code = request.POST.get("lobby_code")

    if len(lobby_code) > 6:
        try:
            return redirect(lobby_code)
        except:
            context = {"error_message": f"This invite isn't valid."}
            return render(
                request, "fulabra_app/partials/error_message.html", {"context": context}
            )
    return redirect("lobby_invite", lobby_code=lobby_code)


def create_lobby_view(request: HttpRequest):
    user: User = request.user
    user_player = user.player
    LobbyGroup.objects.filter(leader=user_player).update(leader=None)
    new_lobby = LobbyGroup.objects.create(leader=user_player)
    return redirect("lobby_invite", lobby_code=new_lobby.code)


def lobby_invite_view(request: HttpRequest, lobby_code: str = ""):
    lobby_code = lobby_code.upper()
    try:
        lobby = LobbyGroup.objects.get(code=lobby_code)
        if not request.user.is_authenticated:
            context = {
                "error_message": f'You must to be logged in to enter in the lobby "{lobby_code}".'
            }
            return render(request, "fulabra_app/index.html", {"context": context})

        user: User = request.user
        user_player = user.player
        is_player_in_lobby = lobby.memberships.filter(player=user_player).exists()

        if lobby.memberships.count() >= 3 and not is_player_in_lobby:
            context = {"error_message": f'The lobby with code "{lobby_code}" is full.'}
            return render(
                request, "fulabra_app/partials/error_message.html", {"context": context}
            )

    except LobbyGroup.DoesNotExist:
        context = {"error_message": f'There isn\'t a lobby with code "{lobby_code}".'}
        return render(
            request, "fulabra_app/partials/error_message.html", {"context": context}
        )

    lobby_url = reverse("lobby_room", kwargs={"lobby_code": lobby_code})

    if request.headers.get("HX-Request"):
        response = HttpResponse(status=200)
        response["HX-Redirect"] = lobby_url
        return response

    return redirect(lobby_url)


def lobby_room_view(request: HttpRequest, lobby_code: str):
    try:
        lobby = LobbyGroup.objects.get(code=lobby_code)
        if not request.user.is_authenticated:
            context = {
                "error_message": f'You must to be logged in to enter in the lobby "{lobby_code}".'
            }
            return render(request, "fulabra_app/index.html", {"context": context})

        user: User = request.user
        user_player = user.player
        is_player_in_lobby = lobby.memberships.filter(player=user_player).exists()

        if lobby.status != LobbyGroup.LobbyStatus.WAITING and not is_player_in_lobby:
            context = {"error_message": "This lobby already start the match."}
            return render(request, "fulabra_app/index.html", {"context": context})
        else:
            context = {
                "current_lobby": lobby,
                "invite": request.build_absolute_uri(
                    reverse("lobby_invite", kwargs={"lobby_code": lobby.code})
                ),
            }
    except LobbyGroup.DoesNotExist:
        context = {
            "error_message": "This lobby no longer exists.",
        }
        return render(request, "fulabra_app/index.html", {"context": context})

    return render(request, "fulabra_app/lobby.html", {"context": context})


def login_view(request: HttpRequest):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return hx_redirect("index")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "fulabra_app/partials/login_form_inner.html",
                {"form": form},
            )
    else:
        form = LoginForm()

    return render(request, "fulabra_app/login.html", {"form": form})


def logout_view(request: HttpRequest):
    logout(request)
    return redirect("index")


def register_view(request: HttpRequest):
    if request.method == "POST":
        form = PlayerRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return hx_redirect("index")

        if request.headers.get("HX-Request"):
            return render(
                request, "fulabra_app/partials/register_form_inner.html", {"form": form}
            )
    else:
        form = PlayerRegistrationForm()

    return render(request, "fulabra_app/register.html", {"form": form})


def profile_view(request: HttpRequest, username: str):
    user = User.objects.filter(username=username).first()
    user_player = user.player
    logged_user: User = request.user
    is_owner = logged_user.player == user_player

    friend_status = None

    if not is_owner and logged_user.is_authenticated:
        friend_request = FriendRequest.objects.filter(
            Q(from_user=logged_user, to_user=user_player)
            | Q(from_user=user_player, to_user=logged_user)
        ).first()

        if friend_request:
            friend_status = friend_request.status

    context = {
        "user_player": user_player,
        "is_owner": is_owner,
        "friend_status": friend_status,
    }

    return render(request, "fulabra_app/profile.html", context)


def edit_profile_view(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect("login")

    user: User = request.user
    user_player = user.player

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user_player)

        if form.is_valid():
            profile_instance = form.save(commit=False)
            preset = form.cleaned_data.get("selected_preset")

            if preset and not request.FILES.get("avatar"):
                if preset == "default_avatar.png":
                    profile_instance.avatar = "avatars/default_avatar.png"
                else:
                    profile_instance.avatar = f"avatars/{preset}"

            profile_instance.save()
            return redirect("profile", username=user.username)
    else:
        form = UserProfileForm(instance=user_player)

    return render(request, "fulabra_app/edit_profile.html", {"form": form})
