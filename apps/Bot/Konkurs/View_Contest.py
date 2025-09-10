# handlers/admin_contest.py
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from ..models.Konkurs import Contest, ContestParticipant
from ..models.TelegramBot import TelegramUser
from ..decorators import admin_required


@admin_required
async def admin_contest_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konkurs tafsilotlari + boshqaruv tugmalari"""
    query = update.callback_query
    await query.answer()

    contest_id = int(query.data.split("_")[2])
    contest = await sync_to_async(Contest.objects.get)(id=contest_id)

    text = (
        f"🏆 <b>{contest.title}</b>\n\n"
        f"{contest.description or '📄 Tavsif yo‘q'}\n"
        f"⏰ Boshlanish: {contest.start_date}\n"
        f"⏳ Tugash: {contest.end_date}\n"
        f"Faol: {'✅' if contest.is_active else '❌'}\n"
    )

    keyboard = [
        [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"admin_edit_{contest_id}")],
        [InlineKeyboardButton("🗑 O‘chirish", callback_data=f"admin_delete_{contest_id}")],
        [InlineKeyboardButton("👥 Ishtirokchilar", callback_data=f"admin_users_{contest_id}")],
        [InlineKeyboardButton("⏹ Tugatish", callback_data=f"admin_finish_{contest_id}")],
        [InlineKeyboardButton("🎉 G‘olib tanlash", callback_data=f"admin_winner_{contest_id}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_list_contests")],
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 👥 Ishtirokchilarni ko‘rish
@admin_required
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    contest_id = int(query.data.split("_")[2])
    contest = await sync_to_async(Contest.objects.get)(id=contest_id)
    participants = await sync_to_async(lambda: list(contest.participants.select_related("user")) )()

    if not participants:
        await query.edit_message_text("❌ Bu konkursda ishtirokchi yo‘q.")
        return

    text = f"👥 <b>{contest.title}</b> ishtirokchilari:\n\n"
    for p in participants:
        text += f"#{p.order_number} — {p.user.first_name or ''} @{p.user.username or ''}\n"

    await query.edit_message_text(text, parse_mode="HTML")


# 🎉 G‘olib tanlash menyusi
@admin_required
async def admin_winner_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    contest_id = int(query.data.split("_")[2])
    context.user_data["contest_id"] = contest_id

    keyboard = [
        [InlineKeyboardButton("🔄 Tasodifiy tanlash", callback_data="winner_random")],
        [InlineKeyboardButton("🔢 Raqam kiritish", callback_data="winner_manual")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"admin_contest_{contest_id}")]
    ]
    await query.edit_message_text(
        "🎉 G‘olibni tanlash usulini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )




@sync_to_async
def get_contest_with_participants(contest_id):
    contest = Contest.objects.get(id=contest_id)
    participants = list(
        contest.participants.select_related("user").all()
    )
    return contest, participants


# 🔄 Tasodifiy tanlash
@admin_required
async def winner_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    contest_id = context.user_data.get("contest_id")
    contest, participants = await get_contest_with_participants(contest_id)

    if not participants:
        await query.edit_message_text("❌ Ishtirokchilar yo‘q.")
        return

    winner = random.choice(participants)
    user = winner.user  # Endi bu joyda ORM query bo‘lmaydi

    # Adminga xabar
    text = (
        f"🎉 <b>G‘olib aniqlangan:</b>\n\n"
        f"🏆 {contest.title}\n"
        f"👤 {user.first_name or ''} @{user.username or ''}\n"
        f"📌 Tartib raqami: {winner.order_number}\n"
        f"⏰ Qo‘shilgan: {winner.joined_at.strftime('%Y-%m-%d %H:%M')}"
    )
    await query.edit_message_text(text, parse_mode="HTML")

    # Userga xabar
    await context.bot.send_message(
        chat_id=user.user_id,
        text=(
            f"🎉 Tabriklaymiz!\n\n"
            f"Siz <b>{contest.title}</b> konkursida g‘olib bo‘ldingiz! 🏆\n\n"
            f"Adminlar 24 soat ichida siz bilan bog‘lanadi.\n"
            f"Aks holda @Asrorbek_10_02 ga murojaat qiling."
        ),
        parse_mode="HTML"
    )

# 🔢 Raqam kiritish (boshlash)
@admin_required
async def winner_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    contest_id = context.user_data.get("contest_id")
    context.user_data["awaiting_winner_number"] = contest_id

    await query.edit_message_text(
        "🔢 G‘olibning tartib raqamini yuboring:"
    )


# 🔢 Raqam qabul qilish
@admin_required
async def set_manual_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_winner_number" not in context.user_data:
        return  # bu admin g‘olib tanlash rejimida emas

    contest_id = context.user_data.pop("awaiting_winner_number")
    try:
        order_number = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Faqat raqam yuboring.")
        return

    contest = await sync_to_async(Contest.objects.get)(id=contest_id)
    winner = await sync_to_async(
        lambda: ContestParticipant.objects.filter(contest=contest, order_number=order_number).first()
    )()

    if not winner:
        await update.message.reply_text("❌ Bunday raqamli ishtirokchi yo‘q.")
        return

    user = winner.user
    # Adminga xabar
    await update.message.reply_text(
        f"🎉 Siz qo‘lda g‘olib tanladingiz:\n\n"
        f"🏆 {contest.title}\n"
        f"👤 {user.first_name or ''} @{user.username or ''}\n"
        f"📌 Tartib raqami: {winner.order_number}\n"
        f"⏰ Qo‘shilgan: {winner.joined_at.strftime('%Y-%m-%d %H:%M')}",
        parse_mode="HTML"
    )

    # Userga xabar
    await context.bot.send_message(
        chat_id=user.user_id,
        text=(
            f"🎉 Tabriklaymiz!\n\n"
            f"Siz <b>{contest.title}</b> konkursida g‘olib bo‘ldingiz! 🏆\n\n"
            f"Adminlar 24 soat ichida siz bilan bog‘lanadi.\n"
            f"Aks holda @Asrorbek_10_02 ga murojaat qiling."
        ),
        parse_mode="HTML"
    )
