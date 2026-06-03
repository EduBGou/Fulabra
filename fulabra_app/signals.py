from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from fulabra_app.models import LobbyGroup, Player, User

@receiver(post_save, sender=User)
def create_user(sender, instance: User, created, **kwargs):
    if created:
        Player.objects.create(user=instance, nickname=instance.username)


@receiver(pre_save, sender=LobbyGroup)
def create_user(sender, instance: LobbyGroup, **kwargs):
    if not instance.code:
        instance.code = instance.generate_unique_code()