from django.db import IntegrityError

from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse

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
