from django.db import IntegrityError

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse

from .models import *


def index(request: HttpRequest):
    return render(request, "fulabra_app/index.html")


def check_lobby(request: HttpRequest, lobby_code: str = ""):
    if lobby_code == "":
        lobby_code = request.POST.get("lobby_code")

    try:
        lobby = LobbyGroup.objects.get(code=lobby_code)
        if lobby.players.count() >= 3:
            context = {"message": f'The lobby with code "{lobby_code}" is full.'}
            return render(request, "fulabra_app/partials/error_message.html", context)

    except LobbyGroup.DoesNotExist:
        context = {"message": f'There isn\'t a lobby with code "{lobby_code}".'}
        return render(request, "fulabra_app/partials/error_message.html", context)

    redirect_url = reverse("lobby_room", kwargs={"lobby_code": lobby_code})

    if request.headers.get("HX-Request"):
        response = HttpResponse(status=200)
        response["HX-Redirect"] = redirect_url
        return response

    return redirect(redirect_url)


def lobby_room(request: HttpRequest, lobby_code: str):
    lobby = get_object_or_404(LobbyGroup, code=lobby_code)
    context = {
        "lobby_code": lobby.code,
        "invite": request.build_absolute_uri(
            reverse("lobby_invite", kwargs={"lobby_code": lobby.code})
        ),
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
                {"message": "Invalid username and/or password."},
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
            context["message"] = "Passwords must match."
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
                context["message"] = "Username already taken."
                context["error"] = "username"
            else:
                context["message"] = "This email is already registered."
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
