from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from django.utils import timezone
from ..models.Konkurs import Contest
from ..decorators import admin_required
from asgiref.sync import sync_to_async


@sync_to_async
def get_contests():
    return list(Contest.objects.order_by("-start_date"))


def chunk_list(lst, n):
    """Ro‘yxatni n elementdan guruhlash"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@admin_required
async def konkurslar_royxati(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contests = await get_contests()  # ORM chaqiruvini async qilamiz
    
    if not contests:
        await update.message.reply_text("📭 Hozircha konkurs mavjud emas")
        return

    buttons = []
    message_text = "<b>✏️ Tahrirlamoqchi bo'lgan konkursni tanlang:</b>\n\n"
    has_inactive = False

    for idx, contest in enumerate(contests, start=1):
        if contest.is_active:
            symbol = "🔹"
        else:
            symbol = "🔸"
            has_inactive = True

        # Xabar matniga qo‘shamiz (raqamlanib)
        message_text += f"{idx}. {symbol} {contest.title}\n"

        # Inline button yaratamiz
        buttons.append(
            InlineKeyboardButton(
                f"{contest.title} {symbol}",
                callback_data=f"admin_contest_{contest.id}"
            )
        )

    # 3 tadan chiqarish
    keyboard = list(chunk_list(buttons, 3))

    # Agar nofaol konkurs bo‘lsa pastiga qo‘shimcha yozuv
    if has_inactive:
        message_text += "\n\n🔹 — Faol\n🔸 — Nofaol"

    reply_markup = InlineKeyboardMarkup(keyboard)

    # callback_query yoki message bo‘yicha javob
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text, reply_markup=reply_markup, parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            message_text, reply_markup=reply_markup, parse_mode="HTML"
        )
