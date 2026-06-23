from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from fulabra_app.models import Game, GameRound, LobbyGroup, Player, User, LobbyPlayer

@receiver(post_save, sender=User)
def create_user(sender, instance: User, created, **kwargs):
    if created:
        Player.objects.create(user=instance, nickname=instance.username)


@receiver(pre_save, sender=LobbyGroup)
def delete_guest_player_on_lobby_leave(sender, instance: LobbyGroup, **kwargs):
    if not instance.code:
        instance.code = instance.generate_unique_code()


@receiver(post_delete, sender=LobbyPlayer)
def delete_guest_player_on_lobby_leave(sender, instance: LobbyPlayer, **kwargs):
    player = instance.player
    if not player.user:
        player.delete()
