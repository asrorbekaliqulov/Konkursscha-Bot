from asgiref.sync import sync_to_async
from .models.TelegramBot import TelegramUser, Channel, Referral
import requests
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Bot
from dotenv import load_dotenv
import os

load_dotenv()

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")

async def save_user_to_db(data, referral_code: str = None):
    user_id = data.id
    first_name = data.first_name
    username = data.username

    @sync_to_async
    def update_or_create_user():
        user, created = TelegramUser.objects.update_or_create(
            user_id=user_id,
            defaults={
                'first_name': first_name,
                'username': username,
            }
        )

        # referral_code bor va bu yangi user bo‘lsa (self-referral emasligi kerak)
        if referral_code and created:
            try:
                referrer = TelegramUser.objects.get(referral_code=referral_code)
                print(referrer)
                # O‘zi o‘zini taklif qilgan bo‘lmasin
                if referrer != user:
                    # Referral yozuvini yaratamiz
                    Referral.objects.create(
                        referrer=referrer,
                        referred_user=user,
                    )
            except TelegramUser.DoesNotExist:
                print(f"Referral code {referral_code} not found")

        return user, created

    try:
        user, created = await update_or_create_user()
        return True
    except Exception as error:
        print(f"Error saving user to DB: {error}")
        return False


@sync_to_async
def create_channel(chat_id, chat_name: str, chat_type: str, url=None):
    channel = Channel.objects.create(
        channel_id=chat_id,
        name=chat_name,
        type=chat_type,
        url=url
    )
    return channel


@sync_to_async
def create_referral(referrer, referred_user, referral_price=0.0):
    referral = Referral.objects.create(
        referrer=referrer,
        referred_user=referred_user,
        referral_price=referral_price
    )
    return referral



def quotes():
    url = "https://quotes-api-self.vercel.app/quote"
    result = requests.get(url)
    return result.json()

@sync_to_async
def get_all_channels():
    return list(Channel.objects.all())


async def get_unsubscribed_channels(user_id: int, bot):
    unsubscribed = []
    channels = await get_all_channels()

    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                unsubscribed.append(channel)
        except Exception as e:
            print(f"Kanal tekshiruvda xatolik: {e}")
            unsubscribed.append(channel)  # Hatolik bo'lsa ham ro'yxatga qo'shish mumkin

    return unsubscribed


async def notify_admins_unable_to_check(user, condition):
    bot = Bot(token=TOKEN)

    text = (
        f"⚠️ Shartni tekshirishda muammo!\n\n"
        f"👤 User: {user}\n"
        f"📌 Shart: {condition.get_condition_type_display()} ({condition.value})\n"
        f"❗ Bot kanalga admin emas."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Bajargan", callback_data=f"cond_admin_yes:{user.user_id}:{condition.id}"),
            InlineKeyboardButton("❌ Bajarmagan", callback_data=f"cond_admin_no:{user.user_id}:{condition.id}")
        ]
    ])

    admin_ids = TelegramUser.objects.filter(is_admin=True).values_list("user_id", flat=True)
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard)
        except:
            pass
