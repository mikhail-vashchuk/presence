from django.contrib import admin

from .models import Invitation, Response, Moment, Presence


admin.site.register(Invitation)
admin.site.register(Response)
admin.site.register(Moment)
admin.site.register(Presence)
