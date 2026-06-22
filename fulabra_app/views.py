from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.db.models import Q
from django.core.cache import cache

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
                player.lobby_membership.delete()
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

    is_player_in_lobby = lobby.lobby_memberships.filter(player=player).exists()

    if lobby.status == LobbyGroup.LobbyStatus.PLAYING and not is_player_in_lobby:
        return render(
            request,
            "fulabra_app/index.html",
            {"context": {"error_message": "This lobby already start the match."}},
        )

    return render(
        request,
        "fulabra_app/lobby.html",
        {"context": LobbyContext(lobby, player, invite_to_lobby(lobby))},
    )


def login_view(request: HttpRequest):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if next_url:
                if request.headers.get("HX-Request"):
                    response = HttpResponse()
                    response["HX-Redirect"] = next_url
                    return response
                return redirect(next_url)
            
            return hx_redirect("index")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "fulabra_app/partials/login_form_inner.html",
                {"form": form, "next_url":next_url},
            )
    else:
        form = LoginForm()

    return render(request, "fulabra_app/login.html", {"form": form, "next_url": next_url})


def logout_view(request: HttpRequest):
    logout(request)
    return redirect("index")


def register_view(request: HttpRequest):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
        
            if next_url:
                if request.headers.get("HX-Request"):
                    response = HttpResponse()
                    response["HX-Redirect"] = next_url
                    return response
                return redirect(next_url)
                
            return hx_redirect("index")

        if request.headers.get("HX-Request"):
            return render(
                request, "fulabra_app/partials/register_form_inner.html", 
                {"form": form, "next_url": next_url}
            )
    else:
        form = UserRegistrationForm()

    return render(request, "fulabra_app/register.html", {"form": form, "next_url": next_url})


def profile_view(request: HttpRequest, username: str):
    user = User.objects.filter(username=username).first()
    if not user:
        return redirect("index")
    
    user_player = user.player
    logged_user: User = request.user
    is_owner = logged_user == user

    friend_status = None

    if not is_owner and logged_user.is_authenticated:
        if logged_user.friends.filter(id=user.id).exists():
            friend_status = "accepted"
        else:
            friend_request = FriendRequest.objects.filter(
                Q(from_user=logged_user, to_user=user)
                | Q(from_user=user, to_user=logged_user)
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


def inbox_view(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect("login")
    
    notifications = request.user.notifications.filter(is_read=False).order_by("-created_at") 

    return render(request, "fulabra_app/inbox.html", {"notifications": notifications})


def notification_action_view(request: HttpRequest, notification_id: int):
    if request.method == "POST":
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        action = request.POST.get("action")

        if notification.notification_type == "friend_request":
            friend_request = FriendRequest.objects.filter(id=notification.target_id).first()
            if friend_request:
                if action == "accept":
                    friend_request.status = "accepted"
                    request.user.friends.add(friend_request.from_user)
                    friend_request.from_user.friends.add(request.user)
                elif action == "reject":
                    friend_request.status = "rejected"
                friend_request.save()
        
        elif notification.notification_type == "game_invite":
            if action == "accept":
                lobby = LobbyGroup.objects.filter(id=notification.target_id).first()

                notification.is_read = True
                notification.save()
                
                if lobby:
                    return hx_redirect("lobby_invite", kwargs={"lobby_code": lobby.code})
                else:
                    return HttpResponse("Lobby no longer exists", status=404)
            elif action == "reject":
                notification.is_read = True
                notification.save()

                # Se o convite foi recusado, libera o botão de volta pra enviar convite
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{notification.sender.username}",
                    {"type": "trigger_sidebar_refresh"}
                )
        
        notification.is_read = True
        notification.save()

        # Se o inbox zerou as notificações
        unread_count = request.user.notifications.filter(is_read=False).count()
        if unread_count == 0:
            empty_state_html = '''
            <div id="empty-inbox-msg" class="text-center py-5 text-muted">
                <i class="bi bi-envelope-open display-1 mb-3 d-block"></i>
                <p class="fs-5 m-0">Your inbox is empty.</p>
                <p class="small">You're all caught up!</p>
            </div>
            '''
            return HttpResponse(empty_state_html)

        return HttpResponse("")
    return HttpResponse("Invalid Request", status=400)


def notification_count(request: HttpRequest):
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
        return {"unread_notifications_count": count}
    return {"unread_notifications_count": 0}


def add_friend_view(request: HttpRequest, player_id: int):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)
    
    to_player = get_object_or_404(Player, id=player_id)

    to_user = to_player.user
    from_user = request.user

    # Para não criar pedidos duplicados
    friend_request, created = FriendRequest.objects.update_or_create(
        from_user=from_user,
        to_user=to_user,
        defaults={"status": "pending"}
    )

    return HttpResponse(
        '<button class="btn btn-secondary rounded-pill px-4 fw-bold shadow-sm" disabled>'
        '<i class="bi bi-clock-history me-2"></i> Request Pending'
        '</button>' 
    )


def remove_friend_view(request: HttpRequest, username: str):
    if not request.user.is_authenticated or request.method != "POST":
        return HttpResponse("Unauthorized", status=401)
    
    friend_to_remove = get_object_or_404(User, username=username)
    request.user.friends.remove(friend_to_remove)

    FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=friend_to_remove) |
        Q(from_user=friend_to_remove, to_user=request.user)
    ).delete()

    return HttpResponse("")


def friends_list_view(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect("login")
    
    friends = request.user.friends.all()

    for friend in friends:
        status = cache.get(f"user_online_{friend.id}", "offline")
        friend.online_status = status

    return render(request, "fulabra_app/friends_list.html", {"friends": friends})


def search_friends_view(request: HttpRequest):
    if not request.user.is_authenticated:
        return HttpResponse("")
    
    query = request.GET.get("q", "").strip()
    if len(query) < 3:
        return HttpResponse("") # Impede a busca com menos de 3 caracteres
    
    results = request.user.friends.filter(
        Q(username_icontains=query) | Q(player__nickname__icontains=query)
    )

    return render(request, "fulabra_app/partials/search_results.html", {"results": results})


def search_users_view(request: HttpRequest):
    if not request.user.is_authenticated:
        return HttpResponse("")
    
    query = request.GET.get("q", "").strip()
    if len(query) < 3:
        return HttpResponse("") # Impede a busca com menos de 3 caracteres
    
    # Não busca pelo próprio usuario nem amigos
    results = User.objects.filter(
        Q(username__icontains=query)
    ).exclude(id=request.user.id).exclude(id__in=request.user.friends.all())[:10]

    return render(request, "fulabra_app/partials/search_results.html", {"results": results})


def invite_link_view(request: HttpRequest, username: str):
    if not request.user.is_authenticated:
        return redirect(f"/login?next=/invite/{username}/")
    
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return redirect("profile", username=request.user.username)
    
    if request.user in target_user.friends.all():
        return redirect("profile", username=target_user.username)
    
    request.user.friends.add(target_user)

    FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=target_user) |
        Q(from_user=target_user, to_user=request.user)
    )

    return redirect("profile", username=target_user.username)


def invite_friend_to_lobby_view(request: HttpRequest, lobby_code: str, friend_id: int):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)
    
    lobby = get_object_or_404(LobbyGroup, code=lobby_code)

    if lobby.lobby_memberships.count() >= 3:
        return HttpResponse(
            '<button type="button" class="btn btn-sm btn-dark rounded-pill px-3 fw-bold" disabled>'
            '<i class="bi bi-slash-circle me-1"></i> Lobby Full'
            '</button>'
        )

    friend = get_object_or_404(User, id=friend_id)

    note, created = Notification.objects.get_or_create(
        recipient=friend,
        sender=request.user,
        notification_type="game_invite",
        target_id=lobby.id,
        defaults={"is_read": False}
    )

    # Se já existia mas estava lido, reativa ele
    if not created and note.is_read:
        note.is_read = False

        import django.utils.timezone
        note.created_at = django.utils.timezone.now() # Atualiza a hora pro topo da lista
        
        note.save()
    elif created:
        note.is_read = False
        note.save()

    return HttpResponse(
        '<button type="button" class="btn btn-sm btn-success rounded-pill px-3 fw-bold" disabled>'
        '<i class="bi bi-check-lg me-1"></i> Sent!'
        '</button>'
    )


def lobby_online_friends_view(request: HttpRequest, lobby_code: str):
    lobby = get_object_or_404(LobbyGroup, code=lobby_code)

    context = LobbyContext(lobby, request.user.player, invite_to_lobby(lobby))
    return render(request, "fulabra_app/partials/online_friends_list.html", {"context": context})