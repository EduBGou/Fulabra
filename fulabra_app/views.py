from sqlite3 import IntegrityError

from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest

from fulabra_app.models import User

def index(request: HttpRequest):
    return render(request, "fulabra_app/index.html")


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
        if password != confirmation:
            return render(
                request,
                "fulabra_app/register.html",
                {"message": "Passwords must match."},
            )
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(
                request,
                "fulabra_app/register.html",
                {"message": "Username already taken."},
            )
        login(request, user)
        return redirect("index")
    else:
        return render(request, "fulabra_app/register.html")
