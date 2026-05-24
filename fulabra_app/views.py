from django.db import IntegrityError

from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

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
            return render(request, "fulabra_app/partials/error_message.html", context)
    return redirect("lobby_invite", lobby_code=lobby_code)


def create_lobby_view(request: HttpRequest):
    LobbyGroup.objects.filter(leader=request.user).update(leader=None)
    new_lobby = LobbyGroup.objects.create(leader=request.user)
    return redirect("lobby_invite", lobby_code=new_lobby.code)


def lobby_invite_view(request: HttpRequest, lobby_code: str = ""):
    lobby_code = lobby_code.upper()
    try:
        lobby = LobbyGroup.objects.get(code=lobby_code)
        if lobby.players.count() >= 3:
            context = {"error_message": f'The lobby with code "{lobby_code}" is full.'}
            return render(request, "fulabra_app/partials/error_message.html", context)

    except LobbyGroup.DoesNotExist:
        context = {"error_message": f'There isn\'t a lobby with code "{lobby_code}".'}
        return render(request, "fulabra_app/partials/error_message.html", context)

    lobby_url = reverse("lobby_room", kwargs={"lobby_code": lobby_code})

    if request.headers.get("HX-Request"):
        response = HttpResponse(status=200)
        response["HX-Redirect"] = lobby_url
        return response

    return redirect(lobby_url)


def lobby_room_view(request: HttpRequest, lobby_code: str):
    try:
        lobby = LobbyGroup.objects.get(code=lobby_code)
        context = {
            "current_lobby": lobby,
            "invite": request.build_absolute_uri(
                reverse("lobby_invite", kwargs={"lobby_code": lobby.code})
            ),
        }
    except:
        context = {
            "error_message": "This invite isn't valid.",
        }

    return render(request, "fulabra_app/lobby.html", context)


def login_view(request: HttpRequest):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            return render(
                request,
                "fulabra_app/login.html",
                {"error_message": "Invalid username and/or password."},
            )
    return render(request, "fulabra_app/login.html")


def logout_view(request: HttpRequest):
    logout(request)
    return redirect("index")


def register(request: HttpRequest):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]

        context = {}
        context["username_val"] = username
        context["email_val"] = email
        context["confirm_value"] = confirmation

        if password != confirmation:
            context["error"] = "confirmation"
            context["confirm_value"] = ""
            context["error_message"] = "Passwords must match."
            return render(
                request,
                "fulabra_app/partials/register_message.html",
                context,
            )
        try:
            user = User.objects.create_user(username, email, password)
        except IntegrityError as e:

            error_msg = str(e).lower()
            if "username" in error_msg:
                context["error_message"] = "Username already taken."
                context["error"] = "username"
            else:
                context["error_message"] = "This email is already registered."
                context["error"] = "email"

            return render(
                request,
                "fulabra_app/partials/register_message.html",
                context,
            )

        login(request, user)

        response = HttpResponse()
        response["HX-Redirect"] = reverse("index")
        return response

    else:
        return render(request, "fulabra_app/register.html")
