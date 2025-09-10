
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from asgiref.sync import sync_to_async
from .models.TelegramBot import Channel, TelegramUser, Referral
import secrets
from telegram.constants import ChatAction
from .utils import save_user_to_db

lists = ["administrator", "member", "creator"]

def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        # Adminni tekshirish
        try:
            user = await TelegramUser.objects.aget(user_id=user_id)  # Django ORM ning asinxron `aget` metodi
            if not user.is_admin:
                await context.bot.send_message(chat_id=user_id, text="Siz admin emassiz!😠")
                return ConversationHandler.END
                
        except TelegramUser.DoesNotExist:
            await context.bot.send_message(chat_id=user_id, text="Sizning ma'lumotlaringiz topilmadi.\n/start")
            return ConversationHandler.END
        
        # Agar admin bo‘lsa, funksiya chaqiriladi
        return await func(update, context, *args, **kwargs)
    return wrapper


# Barcha Channel ma'lumotlarini olish uchun asinxron funksiya
@sync_to_async
def get_all_channels():
    return list(Channel.objects.all())  # QuerySet ni ro'yxatga aylantirish

def mandatory_channel_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if context.args and len(context.args) > 0:
            ref_code = context.args[0]
            if ref_code.startswith("ref_"):
                ref_code = ref_code[4:]
                context.user_data["referral_code"] = ref_code
        else:
            ref_code = None
        # InlineKeyboard uchun tugmalar yaratish
        keyboards = []

        # Barcha kanallarni olish (bazadan yoki listdan)
        channels = await get_all_channels()

        for channel in channels:
            keyboards.append([InlineKeyboardButton(text=channel.name, url=channel.url)])
        keyboards.append([InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data=f"check_subscription_{ref_code}")])
        # Foydalanuvchini har bir kanalga obuna ekanligini tekshirish
        for channel in channels:
            try:
                member = await context.bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    # A'zo emas
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Iltimos, quyidagi kanallarga a'zo bo'ling. So'ngra botdan foydalanishni davom ettiring 👇",
                        reply_markup=InlineKeyboardMarkup(keyboards)
                    )
                    return
            except Exception as e:
                print(f"Kanal tekshiruvda xatolik: {e}")
                continue

        # Agar foydalanuvchi barcha kanallarga obuna bo‘lsa, funksiyani davom ettirish
        return await func(update, context, *args, **kwargs)

    return wrapper


def typing_action(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await context.bot.send_chat_action(chat_id=update.effective_user.id, action=ChatAction.TYPING)
        return await func(update, context, *args, **kwargs)
    return wrapper



def referral_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_data = update.effective_user
        user_id = user_data.id
        first_name = user_data.first_name
        username = user_data.username

        user_exists = await sync_to_async(TelegramUser.objects.filter(user_id=user_id).exists)()
        if user_exists:
            return await func(update, context, *args, **kwargs)

        # Foydalanuvchini yaratamiz
        referral_code = secrets.token_hex(4)  # 8 ta belgili unique referral code
        new_user = await sync_to_async(TelegramUser.objects.create)(
            user_id=user_id,
            first_name=first_name,
            username=username,
            referral_code=referral_code
        )

        # Referral kodni olish
        ref_code = context.user_data.get("referral_code")
        if not ref_code:
            return await func(update, context, *args, **kwargs)

        try:
            referrer = await sync_to_async(TelegramUser.objects.get)(referral_code=ref_code)
            
            # Referral modelga yozish
            await sync_to_async(Referral.objects.create)(
                referrer=referrer,
                referred_user=new_user
            )

            # 🔥 Referral ball qo‘shish
            referrer.ref_score += 1
            await sync_to_async(referrer.save)(update_fields=["ref_score"])

        except TelegramUser.DoesNotExist:
            pass  # noto‘g‘ri referral kod bo‘lsa, e'tibor bermaymiz

        return await func(update, context, *args, **kwargs)
    return wrapper
