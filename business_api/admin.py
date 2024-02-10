from django.contrib import admin

from business_api import models
from rest_framework.authtoken.models import Token

# Register your models here.
admin.site.register(models.CustomUser)


