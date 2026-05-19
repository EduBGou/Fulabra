from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    email = models.EmailField(("email address"), blank=True, unique=True)


class Lobby(models.Model):
    code = models.CharField(max_length=8)
