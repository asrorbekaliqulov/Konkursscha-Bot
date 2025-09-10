from django.contrib import admin
from ..models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from ..models.Konkurs import ConditionCheck, Contest, ContestCondition, ContestParticipant
from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(TelegramUser)
class UserAdmin(ModelAdmin):
    list_display = ("user_id", "first_name", "username", "is_active", "is_admin", "date_joined", "last_active")
    list_filter = ("is_active", "is_admin")
    search_fields = ("username", "first_name")
    ordering = ("user_id", "-date_joined", "last_active")  # Teskari tartibda ko'rsatish
    readonly_fields = ("user_id", 'referral_code', "date_joined", "last_active")
    fieldsets = (
        (None, {
            'fields': ('user_id', 'first_name', 'username', 'referral_code', 'is_active', 'is_admin', 'date_joined', 'last_active', 'ref_score')
        }),
    )
    list_editable = ("is_active", "is_admin")


@admin.register(Channel)
class ChannelAdmin(ModelAdmin):
    list_display = ('name', 'type', 'url', 'channel_id')  # Jadval ustunlari
    list_filter = ('type',)  # Filtrlash uchun ustunlar
    search_fields = ('name', 'channel_id')  # Qidiruv uchun ustunlar


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = ('referrer', 'referred_user', 'created_at')  # Jadval ustunlari
    search_fields = ('referrer__username', 'referred_user__username')  # Qidiruv uchun ustunlar

@admin.register(Guide)
class GuideAdmin(ModelAdmin):
    list_display = ('title', 'status', 'created_at')
    search_fields = ('title', 'content')

@admin.register(Appeal)
class AppealAdmin(ModelAdmin):
    list_display = ('user', 'message', 'created_at')
    search_fields = ('user__username', 'message')
    list_filter = ('created_at',)



class ContestConditionInline(admin.TabularInline):
    model = ContestCondition
    extra = 1
    fields = ("condition_type", "value", "is_required")
    show_change_link = True


class ContestParticipantInline(admin.TabularInline):
    model = ContestParticipant
    extra = 0
    readonly_fields = ("user", "joined_at", "progress_percent")
    show_change_link = True

    def progress_percent(self, obj):
        return f"{obj.progress_percent()}%"
    progress_percent.short_description = "Progress"


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "end_date", "is_active", "participants_count")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("title", "description")
    inlines = [ContestConditionInline, ContestParticipantInline]

    def participants_count(self, obj):
        return obj.participants.count()
    participants_count.short_description = "Ishtirokchilar soni"


@admin.register(ContestCondition)
class ContestConditionAdmin(admin.ModelAdmin):
    list_display = ("contest", "condition_type", "value", "is_required")
    list_filter = ("condition_type", "is_required")
    search_fields = ("contest__title", "value")


class ConditionCheckInline(admin.TabularInline):
    model = ConditionCheck
    extra = 0
    readonly_fields = ("checked_at",)


@admin.register(ContestParticipant)
class ContestParticipantAdmin(admin.ModelAdmin):
    list_display = ("contest", "user", "joined_at", "progress")
    list_filter = ("contest",)
    search_fields = ("contest__title", "user__username")
    inlines = [ConditionCheckInline]

    def progress(self, obj):
        return f"{obj.completed_conditions_count()} / {obj.total_conditions_count()} ({obj.progress_percent()}%)"
    progress.short_description = "Progress"


@admin.register(ConditionCheck)
class ConditionCheckAdmin(admin.ModelAdmin):
    list_display = ("participant", "condition", "is_completed", "checked_at")
    list_filter = ("is_completed", "condition__condition_type")
    search_fields = ("participant__user__username", "condition__contest__title")

