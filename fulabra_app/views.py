from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.http import HttpRequest
from django.urls import reverse
from django.db.models import Q
from .forms import GuestForm, LoginForm, UserRegistrationForm, EditPlayerForm
from .utils import hx_redirect, invite_to_lobby, lobby_is_full, set_player_preset_avatar
from .contexts import LobbyContext
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
    lobby = LobbyGroup.objects.filter(code=lobby_code).first()

    if not lobby:
        context = {"error_message": f'There isn\'t a lobby with code "{lobby_code}".'}
        return render(
            request, "fulabra_app/partials/error_message.html", {"context": context}
        )

    user: User = request.user
    if user.is_authenticated:
        player = user.player
    else:
        guest_player_id = request.session.get("guest_player_id")
        player = Player.objects.filter(id=guest_player_id).first()

    if lobby_is_full(lobby, player):
        context = {"error_message": f'The lobby with code "{lobby_code}" is full.'}
        return render(
            request, "fulabra_app/partials/error_message.html", {"context": context}
        )

    if not player:
        return (
            hx_redirect("guest_form", {"lobby_code": lobby_code})
            if request.headers.get("HX-Request")
            else redirect("guest_form", lobby_code=lobby_code)
        )

    return (
        hx_redirect("lobby_room", {"lobby_code": lobby_code})
        if request.headers.get("HX-Request")
        else redirect("lobby_room", lobby_code=lobby_code)
    )


def guest_form_view(request: HttpRequest, lobby_code: str = ""):
    lobby = LobbyGroup.objects.filter(code=lobby_code).first()
    if not lobby or lobby_is_full(lobby):
        return redirect("lobby_invite", lobby_code=lobby_code)

    avatar_presets = [
        {"filename": "avatar1.jpg"},
        {"filename": "avatar2.jpg"},
        {"filename": "avatar3.jpg"},
        {"filename": "avatar4.jpg"},
    ]

    if request.method == "POST":
        form = GuestForm(request.POST, request.FILES)
        if form.is_valid():

            player: Player = form.save(commit=False)
            preset = form.cleaned_data.get("selected_preset")
            set_player_preset_avatar(request, player, preset)

            player.save()
            request.session["guest_player_id"] = player.id
            return redirect("lobby_room", lobby_code=lobby_code)
    else:
        if request.session.get("guest_player_id"):
            player = Player.objects.filter(
                id=request.session["guest_player_id"]
            ).first()
            if player:
                player.membership.delete()
                player.delete()
        form = GuestForm()

    return render(
        request,
        "fulabra_app/guest_form.html",
        {"form": form, "lobby_code": lobby_code, "avatar_presets": avatar_presets},
    )


def lobby_room_view(request: HttpRequest, lobby_code: str):
    lobby = LobbyGroup.objects.filter(code=lobby_code).first()

    if not lobby:
        context = {"error_message": "This lobby no longer exists."}
        return render(request, "fulabra_app/index.html", {"context": context})

    user: User = request.user

    if user.is_authenticated:
        player = user.player
    else:
        guest_player_id = request.session.get("guest_player_id")
        player = Player.objects.filter(id=guest_player_id).first()
        if player is None:
            return redirect("lobby_invite", lobby_code=lobby_code)

    is_player_in_lobby = lobby.memberships.filter(player=player).exists()

    if lobby.status != LobbyGroup.LobbyStatus.WAITING and not is_player_in_lobby:
        return render(
            request,
            "fulabra_app/index.html",
            {"context": {"error_message": "This lobby already start the match."}},
        )
    else:
        return render(
            request,
            "fulabra_app/lobby.html",
            {"context": LobbyContext(lobby, player, invite_to_lobby(lobby))},
        )


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
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return hx_redirect("index")

        if request.headers.get("HX-Request"):
            return render(
                request, "fulabra_app/partials/register_form_inner.html", {"form": form}
            )
    else:
        form = UserRegistrationForm()

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
        form = EditPlayerForm(request.POST, request.FILES, instance=user_player)

        if form.is_valid():
            player: Player = form.save(commit=False)
            preset = form.cleaned_data.get("selected_preset")

            set_player_preset_avatar(request, player, preset)

            return redirect("profile", username=user.username)
    else:
        form = EditPlayerForm(instance=user_player)

    return render(request, "fulabra_app/edit_profile.html", {"form": form})
