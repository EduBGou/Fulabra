from django.conf.urls.static import static
from django.urls import include, path
from django.conf import settings
from . import views

urlpatterns = [
    path("", views.index_view, name="index"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("register", views.register_view, name="register"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("lobby", views.handle_lobby_view, name="handle_lobby"),
    path(
        "lobby_invite/<str:lobby_code>/", views.lobby_invite_view, name="lobby_invite"
    ),
    path("create_lobby", views.create_lobby_view, name="create_lobby"),
    path("game/submit_word", views.create_lobby_view, name="submit_word"),
    path("guest_form/<str:lobby_code>/", views.guest_form_view, name="guest_form"),
    path("lobby/<str:lobby_code>/", views.lobby_room_view, name="lobby_room"),
    path("profile/<str:username>/", views.profile_view, name="profile"),
    path("profile/edit", views.edit_profile_view, name="edit_profile"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
