from django.urls import path

from . import views

urlpatterns = [
    path("", views.index_view, name="index"),
    path("register", views.register, name="register"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("lobby", views.handle_lobby_view, name="handle_lobby"),
    path(
        "lobby_invite/<str:lobby_code>/", views.lobby_invite_view, name="lobby_invite"
    ),
    path("create_lobby", views.create_lobby_view, name="create_lobby"),
    path("lobby/<str:lobby_code>/", views.lobby_room_view, name="lobby_room"),
]
