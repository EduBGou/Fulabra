from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest


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
                "network/login.html",
                {"message": "Invalid username and/or password."},
            )
    return render(request, "fulabra_app/login.html")


def logout_view(request: HttpRequest):
    logout(request)
    return redirect("index")
