from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class CustomUser(AbstractUser):
    username = models.CharField(unique=True, max_length=250)
    user_id = models.CharField(max_length=250)
    full_name = models.CharField(max_length=250)
    email = models.EmailField()

