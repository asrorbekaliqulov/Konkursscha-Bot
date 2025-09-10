from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from ..utils import save_user_to_db, quotes, get_unsubscribed_channels
from ..models.TelegramBot import TelegramUser
from ..decorators import typing_action, mandatory_channel_required, referral_handler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove


async def get_user_keyboard():
    """Bot uchun inline keyboardni dinamik yaratish."""
    users_keyboards = [
        [
            InlineKeyboardButton(text="🎁 Konkursda qatnashish", callback_data="contest_list")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Qo'llanma", callback_data='getGuide'),
            InlineKeyboardButton(text="📞 Murojaat", callback_data="appeal")
        ],
        [
            InlineKeyboardButton(text="🔗 Do'stlarni taklif qilish", callback_data="referral"),
        ]
    ]

    return InlineKeyboardMarkup(users_keyboards)



async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ref_code = query.data.split("_")[-1] if "_" in query.data else None

    user_id = query.from_user.id
    unsubscribed_channels = await get_unsubscribed_channels(user_id, context.bot)

    if not unsubscribed_channels:
        # Barcha kanallarga a'zo -> start funksiyasiga yo'naltirish
        await context.bot.send_message(
            chat_id=user_id,
            text="Rahmat! Siz barcha kanallarga a'zo bo'lgansiz ✅\nBotdan foydalanishni davom ettirishingiz mumkin."
        )
        # start handlerni ishlatish:
        return await start(update, context, [ref_code])

    # A'zolik yetishmaydi — qaytadan ro'yxatni ko'rsatish
    keyboard = [
        [InlineKeyboardButton(channel.name, url=channel.url)]
        for channel in unsubscribed_channels
    ]
    keyboard.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data=f"check_subscription_{ref_code}")])
    await update.callback_query.delete_message()
    await context.bot.send_message(
        chat_id=user_id,
        text="Iltimos, quyidagi kanallarga a'zo bo'ling. So'ngra botdan foydalanishni davom ettiring 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@mandatory_channel_required
@referral_handler
@typing_action
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, *args) -> int:
    """
    Botni ishga tushirish uchun komanda.
    """
    remove = ReplyKeyboardRemove()

    data = update.effective_user
    if update.callback_query:
        await update.callback_query.answer("Asosiy menyu")
        await update.callback_query.delete_message()
    reply_markup = await get_user_keyboard()
    # is_save = await save_user_to_db(data, referral_code=ref_code)
    admin_id = await TelegramUser.get_admin_ids()
    if update.effective_user.id in admin_id:
        await context.bot.send_message(chat_id=update.effective_user.id, text="<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>", reply_markup=remove, parse_mode="html")
    quote = quotes()
    quote_message = f"<b>{quote['quote']}</b>\n\n<i>{quote['author']}</i>"
    await context.bot.send_message(chat_id=update.effective_user.id, text=f"<b>Hello 👋\nComing soon</b>\n\n<blockquote>{quote_message}</blockquote>", parse_mode="html", reply_markup=reply_markup) 
    return ConversationHandler.END


    