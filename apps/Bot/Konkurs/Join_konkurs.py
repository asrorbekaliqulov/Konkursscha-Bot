from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from asgiref.sync import sync_to_async
from ..models.Konkurs import Contest, ContestParticipant
from ..models.TelegramBot import TelegramUser
from .service import join_contest


async def show_contests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Konkurslar ro‘yxatini chiqarish"""
    user = update.effective_user
    tg_user, _ = await sync_to_async(TelegramUser.objects.get_or_create)(
        user_id=user.id,
        defaults={"username": user.username, "first_name": user.first_name}
    )

    contests = await sync_to_async(lambda: list(Contest.objects.filter(is_active=True)))()
    if not contests:
        await update.callback_query.edit_message_text("<b>❌ Hozircha faol konkurslar yo‘q.</b>", parse_mode="HTML")
        return

    keyboard = []
    for c in contests:
        participant = await sync_to_async(
            lambda: ContestParticipant.objects.filter(contest=c, user=tg_user).first()
        )()
        if participant:
            status = "🟢"
        elif context.user_data.get(f"failed_{c.id}"):
            status = "🟡"
        else:
            status = "⚪️"

        keyboard.append(
            [InlineKeyboardButton(f"{status} {c.title}", callback_data=f"contest_detail:{c.id}")]
        )

    await update.callback_query.edit_message_text(
        "<b>📋 Faol konkurslar ro‘yxati:</b>\n\n"
        "<blockquote>🟢 — qatnashgan\n"
        "⚪️ — qatnashmagan\n"
        "🟡 — shartlar bajarilmagan</blockquote>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


from ..models.Konkurs import ContestCondition, ConditionCheck

async def contest_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    contest_id = int(query.data.split(":")[1])
    contest = await sync_to_async(Contest.objects.get)(id=contest_id)
    context.user_data["contest_id"] = contest_id

    user = update.effective_user
    tg_user = await sync_to_async(TelegramUser.objects.get)(user_id=user.id)

    participants_count = await sync_to_async(contest.participants.count)()
    participant = await sync_to_async(
        lambda: ContestParticipant.objects.filter(contest=contest, user=tg_user).first()
    )()
    failed_before = context.user_data.get(f"failed_{contest_id}")

    # 📌 Shartlarni olib kelamiz
    conditions = await sync_to_async(lambda: list(contest.conditions.all()))()
    checks = {}
    if participant:
        checks = {
            c.condition.id: c.is_completed
            for c in await sync_to_async(lambda: list(
                ConditionCheck.objects.filter(participant=participant)
            ))()
        }

    text = (
        f"🏆 <b>{contest.title}</b>\n\n"
        f"{contest.description or '📄 Tavsif mavjud emas'}\n\n"
        f"⏰ Boshlanish: {contest.start_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"⏳ Tugash: {contest.end_date.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"👥 Hozircha ishtirokchilar soni: <b>{participants_count}</b> ta\n\n"
        f"<b>🔑 Shartlar:</b>\n"
    )

    for idx, cond in enumerate(conditions, start=1):
        status = "❌"
        if participant:
            if checks.get(cond.id):
                status = "✅"
        text += f"{idx}. {cond.get_condition_type_display()} ({cond.value}) {status}\n"

    keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="contest_back")]]
    if not participant:
        if failed_before:
            keyboard.append([InlineKeyboardButton("🔄 Qayta urinish", callback_data=f"contest_join:{contest_id}")])
        else:
            keyboard.append([InlineKeyboardButton("✅ Qatnashish", callback_data=f"contest_join:{contest_id}")])

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def contest_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konkursga qo‘shilish"""
    query = update.callback_query
    await query.answer()

    contest_id = int(query.data.split(":")[1])
    user = update.effective_user

    tg_user, _ = await sync_to_async(TelegramUser.objects.get_or_create)(
        user_id=user.id,
        defaults={"username": user.username, "first_name": user.first_name}
    )

    result, message = await join_contest(tg_user, contest_id)

    if result == "pending":
        context.user_data[f"failed_{contest_id}"] = True
    elif result is True:
        context.user_data[f"failed_{contest_id}"] = False

    await query.edit_message_text(
        text=message,
        parse_mode="HTML"
    )


async def contest_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Orqaga tugmasi"""
    query = update.callback_query
    await query.answer()

    # `query.message.chat_id` ishlatib, xuddi /show_contests dagidek chiqaramiz
    class FakeUpdate:
        message = query.message
    await show_contests(update, context)


from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from ..models.Konkurs import ConditionCheck, ContestCondition, ContestParticipant
from ..models.TelegramBot import TelegramUser

async def condition_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id, condition_id = query.data.split(":")
    user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
    condition = await sync_to_async(ContestCondition.objects.get)(id=condition_id)

    participant = await sync_to_async(
        lambda: ContestParticipant.objects.filter(contest=condition.contest, user=user).first()
    )()
    if not participant:
        await query.edit_message_text("❌ Bu user konkursda ishtirokchi emas.")
        return

    check = await sync_to_async(
        lambda: ConditionCheck.objects.filter(participant=participant, condition=condition).first()
    )()
    if not check:
        await query.edit_message_text("❌ ConditionCheck topilmadi.")
        return

    if "yes" in action:
        check.is_completed = True
    else:
        check.is_completed = False
    await sync_to_async(check.save)()

    await query.edit_message_text(
        f"✅ Admin tomonidan belgilandi: {user} — {condition.get_condition_type_display()} → {'Bajarildi' if check.is_completed else 'Bajarilmadi'}"
    )


