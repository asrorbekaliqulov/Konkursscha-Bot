from django.db import models


class Contest(models.Model):
    title = models.CharField(max_length=255, verbose_name="Konkurs nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    start_date = models.DateTimeField(verbose_name="Boshlanish sanasi")
    end_date = models.DateTimeField(verbose_name="Tugash sanasi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")

    class Meta:
        verbose_name = "Konkurs"
        verbose_name_plural = "Konkurslar"

    def __str__(self):
        return self.title


class ContestCondition(models.Model):
    CONDITION_TYPES = [
        ("subscribe_channel", "Kanalga obuna bo‘lish"),
        ("invite_users", "Ma’lum miqdorda foydalanuvchi taklif qilish"),
        ("bot_start", "Boshqa botga /start bosish"),
        ("site_register", "Saytda ro‘yxatdan o‘tish"),
        ("site_activity", "Saytda faol bo‘lish"),
    ]

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="conditions",
        verbose_name="Konkurs"
    )
    condition_type = models.CharField(
        max_length=50, choices=CONDITION_TYPES, verbose_name="Shart turi"
    )
    value = models.CharField(
        max_length=255,
        verbose_name="Qiymat",
        blank=True,
        null=True,
        help_text=(
            "Shartga qarab: "
            "kanal username/link, "
            "talab qilingan user soni, "
            "bot username, "
            "faollik muddati (kunlarda) va hokazo"
        )
    )
    is_required = models.BooleanField(default=True, verbose_name="Majburiymi?")

    class Meta:
        verbose_name = "Konkurs sharti"
        verbose_name_plural = "Konkurs shartlari"

    def __str__(self):
        return f"{self.contest.title} - {self.get_condition_type_display()}"


class ContestParticipant(models.Model):
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="Konkurs"
    )
    user = models.ForeignKey(
        "TelegramUser",
        on_delete=models.CASCADE,
        related_name="contests",
        verbose_name="Foydalanuvchi"
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Ishtirokchi qo‘shilgan sana")
    order_number = models.PositiveIntegerField(verbose_name="Ishtirokchi tartib raqami", blank=True, null=True)


    class Meta:
        unique_together = ("contest", "user")
        verbose_name = "Konkurs ishtirokchisi"
        verbose_name_plural = "Konkurs ishtirokchilari"

    def __str__(self):
        return f"{self.user} - {self.contest.title}"

    def completed_conditions_count(self):
        return self.condition_checks.filter(is_completed=True).count()

    def total_conditions_count(self):
        return self.contest.conditions.count()

    def progress_percent(self):
        total = self.total_conditions_count()
        if total == 0:
            return 0
        return int((self.completed_conditions_count() / total) * 100)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            last_number = ContestParticipant.objects.filter(contest=self.contest).count()
            self.order_number = last_number + 1
        super().save(*args, **kwargs)


class ConditionCheck(models.Model):
    participant = models.ForeignKey(
        ContestParticipant,
        on_delete=models.CASCADE,
        related_name="condition_checks",
        verbose_name="Ishtirokchi"
    )
    condition = models.ForeignKey(
        ContestCondition,
        on_delete=models.CASCADE,
        related_name="checks",
        verbose_name="Shart"
    )
    is_completed = models.BooleanField(default=False, verbose_name="Bajarildimi?")
    checked_at = models.DateTimeField(auto_now=True, verbose_name="Tekshirilgan vaqt")

    class Meta:
        unique_together = ("participant", "condition")
        verbose_name = "Shart bajarilishi"
        verbose_name_plural = "Shartlar bajarilishi"

    def __str__(self):
        return f"{self.participant.user} - {self.condition.get_condition_type_display()} ({'✅' if self.is_completed else '❌'})"
