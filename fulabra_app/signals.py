from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import *

@receiver(post_save, sender=User)
def create_user(sender, instance: User, created, **kwargs):
    if created:
        Player.objects.create(user=instance, nickname=instance.username)


@receiver(pre_save, sender=LobbyGroup)
def delete_guest_player_on_lobby_leave(sender, instance: LobbyGroup, **kwargs):
    if not instance.code:
        instance.code = instance.generate_unique_code()


# @receiver(post_save, sender=Game)
# def create_game(sender, instance: Game, created: bool, **kargs):
#     if created:
#         GameRound.objects.create(game=instance, round_number=0)


@receiver(post_delete, sender=LobbyPlayer)
def delete_guest_player_on_lobby_leave(sender, instance: LobbyPlayer, **kwargs):
    player = instance.player
    if not player.user:
        player.delete()


@receiver(post_save, sender=FriendRequest)
def generic_friend_request_notification(sender, instance, created, **kwargs):
    if instance.status == "pending":
        # Puxa a notificação existente ou cria uma nova
        note, note_created = Notification.objects.get_or_create(
            recipient=instance.to_user,
            sender=instance.from_user,
            notification_type="friend_request",
            target_id=instance.id
        )

        if not note_created and note.is_read:
            note.is_read = False
            note.save()


@receiver(post_save, sender=Notification)
def trigger_notification_websocket(sender, instance: Notification, created, **kwargs):
    channel_layer = get_channel_layer()
    group_name = f"notifications_{instance.recipient.username}"

    message = {
        "type": "send_notification_update",
        "is_read": instance.is_read
    }

    if created:
        message["notification_id"] = instance.id

    async_to_sync(channel_layer.group_send)(group_name, message)


@receiver(post_delete, sender=LobbyGroup)
def cleanup_deleted_lobby_invites(sender, instance: LobbyGroup, **kwargs):
    Notification.objects.filter(
        notification_type="game_invite",
        target_id=instance.id
    ).update(is_read=True)
