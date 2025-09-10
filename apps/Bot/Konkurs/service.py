import requests
from telegram import Bot
from ..utils import notify_admins_unable_to_check
from django.conf import settings

def check_condition(user, condition, bot: Bot):
    """
    Har bir shartni real tekshirish funksiyasi.
    True/False qaytaradi
    """
    user_id = user.user_id
    cond_type = condition.condition_type
    value = condition.value

    try:
        if cond_type == "site_register":
            url = f"http://45.138.656.12:5565/is-register/{user_id}"
            resp = requests.get(url, timeout=5)
            return resp.json() is True

        elif cond_type == "site_activity":
            url = f"http://45.138.656.12:5565/is-user-active/{user_id}"
            resp = requests.get(url, timeout=5)
            days_active = resp.json()
            return int(days_active) >= int(value)

        elif cond_type == "bot_start":
            url = f"http://45.138.656.12:5565/is-member/{user_id}"
            resp = requests.get(url, timeout=5)
            return resp.json() is True

        elif cond_type == "invite_users":
            return user.ref_score >= int(value)

        elif cond_type == "subscribe_channel":
            try:
                member = bot.get_chat_member(chat_id=value, user_id=user_id)
                return member.status in ["member", "administrator", "creator"]
            except Exception:
                notify_admins_unable_to_check(user, condition)
                return False

    except Exception as e:
        print(f"❌ Shart tekshirishda xatolik: {e}")
        return False

    return False



from django.db import transaction
from asgiref.sync import sync_to_async
from ..models.Konkurs import Contest, ContestParticipant, ConditionCheck

async def join_contest(user, contest_id):
    contest = await sync_to_async(
        lambda: Contest.objects.filter(id=contest_id, is_active=True).first()
    )()
    if not contest:
        return False, "❌ Bunday konkurs topilmadi yoki faol emas."

    existing = await sync_to_async(
        lambda: ContestParticipant.objects.filter(contest=contest, user=user).first()
    )()
    if existing:
        return False, f"⚠️ Siz allaqachon konkursga qo‘shilgansiz.\nSizning raqamingiz: {getattr(existing, 'order_number', '❓')}"

    conditions = await sync_to_async(lambda: list(contest.conditions.all()))()

    @sync_to_async
    def create_participant():
        with transaction.atomic():
            return ContestParticipant.objects.create(contest=contest, user=user)

    participant = await create_participant()

    for condition in conditions:
        is_completed = await sync_to_async(check_condition)(user, condition, Bot)

        @sync_to_async
        def save_check():
            return ConditionCheck.objects.create(
                participant=participant,
                condition=condition,
                is_completed=is_completed
            )
        await save_check()

        if condition.condition_type == "invite_users" and is_completed:
            user.ref_score -= int(condition.value)
            await sync_to_async(user.save)(update_fields=["ref_score"])

    completed = await sync_to_async(participant.completed_conditions_count)()
    total = await sync_to_async(participant.total_conditions_count)()

    if completed == total:
        return True, f"🎉 Siz barcha shartlarni bajardingiz va konkursga qo‘shildingiz!\nSizning tartib raqamingiz: {participant.order_number}"
    else:
        return "pending", f"⚠️ Siz barcha shartlarni bajarmadingiz.\nProgress: {completed}/{total}"
