from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("register", views.register, name="register"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("check_lobby", views.check_lobby, name="check_lobby"),
    path("lobby/<str:lobby_code>/", views.lobby_room, name="lobby_room"),
]
