from django.contrib import admin

from .models import (
    AssistantFeedback,
    AssistantHint,
    Invitation,
    Moment,
    Presence,
    Response,
)


admin.site.register(Invitation)
admin.site.register(Response)
admin.site.register(Moment)
admin.site.register(Presence)
admin.site.register(AssistantHint)
admin.site.register(AssistantFeedback)
