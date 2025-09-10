from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from ..decorators import mandatory_channel_required
from asgiref.sync import sync_to_async
from ..models.TelegramBot import TelegramUser, Referral
import uuid


@mandatory_channel_required
async def get_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    usr_info = await sync_to_async(TelegramUser.objects.filter(user_id=user.id).first)()
    if usr_info.referral_code is None:
        usr_info.referral_code = uuid.uuid4().hex[:8]
        await sync_to_async(usr_info.save)(update_fields=['referral_code'])

    bot = await context.bot.get_me()
    referral_link = f"https://t.me/{bot.username}?start=ref_{usr_info.referral_code}"
    await update.callback_query.edit_message_text(f"Sizning referral havolangiz: \n\n{referral_link}")
