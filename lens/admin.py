from django.contrib import admin
from django.contrib import admin
from .models import Attempt, Drawing, Game, MagicLens


@admin.register(MagicLens)
class MagicLensAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "order")
    list_editable = ("is_active", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Drawing)
class DrawingAdmin(admin.ModelAdmin):
    list_display = ("title", "is_template", "is_active")


class AttemptInline(admin.TabularInline):
    model = Attempt
    extra = 0
    can_delete = False
    readonly_fields = ("drawing", "target_lens", "chosen_lens", "is_correct", "seconds", "points", "created_at")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("player_name", "points", "created_at")
    inlines = [AttemptInline]
