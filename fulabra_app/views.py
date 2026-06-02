from django.db import IntegrityError
from django.db.models import Q

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

from .forms import UserProfileForm
from .models import *
from .contexts import RegisterContext


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
    LobbyGroup.objects.filter(leader=request.user).update(leader=None)
    new_lobby = LobbyGroup.objects.create(leader=request.user)
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
        is_player_in_lobby = lobby.memberships.filter(user=request.user).exists()
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

        is_player_in_lobby = lobby.memberships.filter(user=request.user).exists()
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
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return hx_redirect("index")
        else:
            context = {"error_message": "Invalid username and/or password."}
            return render(
                request,
                "fulabra_app/partials/error_message.html",
                {"context": context},
            )
    return render(request, "fulabra_app/login.html")


def logout_view(request: HttpRequest):
    logout(request)
    return redirect("index")


def register_view(request: HttpRequest):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirmation = request.POST.get("confirmation", "")

        print(username, email, password, confirmation)

        context = RegisterContext(username, email, confirmation)

        if len(password) < 8:
            context.error = "password"
            context.confirm_val = ""
            context.error_message = "The password must contain at least 8 characters."
            return render(
                request,
                "fulabra_app/partials/register_message.html",
                {"context": context},
            )

        if password.isnumeric():
            context.error = "password"
            context.confirm_val = ""
            context.error_message = "The password password can't be entirely numeric."
            return render(
                request,
                "fulabra_app/partials/register_message.html",
                {"context": context},
            )

        if password != confirmation:
            context.error = "confirmation"
            context.confirm_val = ""
            context.error_message = "Passwords must match."

            return render(
                request,
                "fulabra_app/partials/register_message.html",
                {"context": context},
            )
        
        try:
            user = User.objects.create_user(username, email, password)
        except IntegrityError as e:

            error_msg = str(e).lower()
            if "username" in error_msg:
                context.error_message = "Username already taken."
                context.error = "username"
            else:
                context.error_message = "This email is already registered."
                context.error = "email"

            return render(
                request,
                "fulabra_app/partials/register_message.html",
                {"context": context},
            )

        login(request, user)

        return hx_redirect("index")

    else:
        return render(request, "fulabra_app/register.html")


# Perfil do Usuário
def profile_view(request: HttpRequest, username: str):
    profile_user = get_object_or_404(User, username=username)
    logged_user = request.user
    is_owner = logged_user == profile_user

    recent_matches = Match.objects.filter(
        Q(player1=profile_user) | Q(player2=profile_user) | Q(player3=profile_user)
    ).order_by("-date_played")[:10]

    friend_status = None

    if not is_owner and logged_user.is_authenticated:
        friend_request = FriendRequest.objects.filter(
            Q(from_user=logged_user, to_user=profile_user)
            | Q(from_user=profile_user, to_user=logged_user)
        ).first()

        if friend_request:
            friend_status = friend_request.status

    context = {
        "profile_user": profile_user,
        "is_owner": is_owner,
        "recent_matches": recent_matches,
        "friend_status": friend_status,
    }

    return render(request, "fulabra_app/profile.html", context)


# Edição de perfil
def edit_profile_view(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect("login")

    logged_user = request.user

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=logged_user)

        if form.is_valid():
            user_instace = form.save(commit=False)
            preset = form.cleaned_data.get("selected_preset")

            if preset and not request.FILES.get("avatar"):
                if preset == "default_avatar.png":
                    user_instace.avatar = "avatars/default_avatar.png"
                else:
                    user_instace.avatar = f"avatars/{preset}"

            user_instace.save()
            return redirect("profile", username=logged_user.username)
    else:
        form = UserProfileForm(instance=logged_user)

    return render(request, "fulabra_app/edit_profile.html", {"form": form})


def hx_redirect(viewname: str):
    response = HttpResponse()
    response["HX-Redirect"] = reverse(viewname)
    return response
