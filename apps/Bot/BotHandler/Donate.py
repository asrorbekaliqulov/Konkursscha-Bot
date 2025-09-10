from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.ext import ContextTypes, ConversationHandler


async def DonateMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Xayriya menyusi.
    """
    if update.callback_query:
        await update.callback_query.answer("Xayriya")
        await update.callback_query.delete_message()

    # Xayriya tugmalari
    donate_keyboard = [
        [
            InlineKeyboardButton(text="💸 Tirikchilik", url="https://tirikchilik.uz/AsrorDev"),
            InlineKeyboardButton(text="💳 Kartani nusxalash", copy_text=CopyTextButton(text="9860 6067 4787 7300")),
        ],
        [
            InlineKeyboardButton(text="🖇 Referral", callback_data="referral")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data='Main_Menu')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(donate_keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_user.id, 
        text="""<b>💰 Loyihalarimizni qo‘llab-quvvatlang

<blockquote>Quyidagi tugmalar orqali istalgan xayriya turini tanlab, loyihamizga o‘z hissangizni qo‘shing!

Sizning xayriyangiz loyihalarimizning davomiyligiga va shunga o‘xshash foydali tashabbuslarning ko‘payishiga xizmat qiladi ✊</blockquote>

📇 Karta orqali: 9860606747877300 | A.A

🫶 Xayriyangiz uchun tashakkur!</b>""",
       reply_markup=reply_markup,
       parse_mode="html"
    )

    return ConversationHandler.END