from ..MandatoryChannel import AddChannel_ConvHandler, MandatoryChannelOrGroupList, start_delete_mandatory, delete_mandatory
from ..BotCommands import start, check_subscription_callback
from ..BotAdmin import admin_menyu, add_admin_handler, the_first_admin, remove_admin_handler, AdminList
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from ..BotHandler import send_msg_handler, bot_stats, edit_bot_bio, InlineButton, guide, guide_create_conv, guide_update_conv, guide_delete_conv, AdminGuide, appeal_conv, list_appeals, show_appeal_detail, handle_admin_reply, all_appeals, DonateMenu, get_referral_link
from ..Konkurs import Conkurs_Conversation, konkurslar_royxati, condition_admin_action, show_contests, contest_detail, contest_join, contest_back, admin_contest_detail, admin_users, admin_winner_menu, winner_random, winner_manual, set_manual_winner
from datetime import datetime, timedelta
from ..BotCommands.DownDB import DownlBD
import random
import os 
from dotenv import load_dotenv

load_dotenv()

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")


async def schedule_next_bio_update(context):
    # Keyingi bio yangilanishi uchun 10-12 soat oralig'ida tasodifiy vaqt tanlash
    hours = random.uniform(10, 12)
    next_time = datetime.now() + timedelta(hours=hours)
    
    # Joriy bio yangilanishini bajarish
    await edit_bot_bio(None, context)
    
    # Keyingi yangilanishni rejalashtirish
    context.job_queue.run_once(schedule_next_bio_update, 
                             when=next_time)

def main():
    # Application yaratishda persistence va job_queue parametrlarini qo'shamiz
    app = Application.builder().token(TOKEN).build()

    # Commands  
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("DownDataBaza", DownlBD))
    app.add_handler(CommandHandler('admin_panel', admin_menyu))
    app.add_handler(CommandHandler('kjiaufuyerfgvu', the_first_admin))
    app.add_handler(CommandHandler('edit_bot_bio', edit_bot_bio))
    
    # Conversation handlers
    app.add_handler(send_msg_handler)
    app.add_handler(add_admin_handler)
    app.add_handler(remove_admin_handler)
    app.add_handler(AddChannel_ConvHandler)
    app.add_handler(guide_create_conv)
    app.add_handler(guide_update_conv)
    app.add_handler(guide_delete_conv)
    app.add_handler(appeal_conv)
    app.add_handler(Conkurs_Conversation)






    # Inline hanlder
    app.add_handler(CallbackQueryHandler(start, pattern=r"^Main_Menu$"))
    app.add_handler(CallbackQueryHandler(bot_stats, pattern=r"^botstats$"))
    app.add_handler(CallbackQueryHandler(start, pattern=r"^cancel$"))
    app.add_handler(CallbackQueryHandler(start_delete_mandatory, pattern=r"^Del_mandatory$"))
    app.add_handler(CallbackQueryHandler(delete_mandatory, pattern=r"^xDeleted_"))
    app.add_handler(CallbackQueryHandler(start, pattern=r"^Check_mandatory_channel$"))
    app.add_handler(CallbackQueryHandler(AdminList, pattern=r"^admin_list$"))
    app.add_handler(CallbackQueryHandler(MandatoryChannelOrGroupList, pattern=r"^mandatory_channel$"))
    app.add_handler(CallbackQueryHandler(start, pattern=r"^BackToMainMenu$"))
    app.add_handler(CallbackQueryHandler(guide, pattern=r"^getGuide$"))
    app.add_handler(CallbackQueryHandler(AdminGuide, pattern=r"^AdminGuide$"))
    app.add_handler(CallbackQueryHandler(list_appeals, pattern=r"^AdminAppeal$"))
    app.add_handler(CallbackQueryHandler(show_appeal_detail, pattern=r"^appeal_detail:\d+$"))
    app.add_handler(CallbackQueryHandler(all_appeals, pattern=r"^all_appeals$"))
    app.add_handler(CallbackQueryHandler(DonateMenu, pattern=r"^donate$"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern=r"^check_subscription_"))
    app.add_handler(CallbackQueryHandler(get_referral_link, pattern=r"^referral$"))
    app.add_handler(CallbackQueryHandler(contest_detail, pattern=r"^contest_detail:"))
    app.add_handler(CallbackQueryHandler(contest_join, pattern=r"^contest_join:"))
    app.add_handler(CallbackQueryHandler(contest_back, pattern=r"^contest_back$"))
    app.add_handler(CallbackQueryHandler(admin_contest_detail, pattern=r"^admin_contest_"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern=r"^admin_users_"))
    app.add_handler(CallbackQueryHandler(admin_winner_menu, pattern=r"^admin_winner_"))
    app.add_handler(CallbackQueryHandler(winner_random, pattern=r"^winner_random$"))
    app.add_handler(CallbackQueryHandler(winner_manual, pattern=r"^winner_manual$"))
    app.add_handler(CallbackQueryHandler(show_contests, pattern=r"^contest_list"))
    app.add_handler(CallbackQueryHandler(condition_admin_action, pattern=r"^cond_admin_"))
    app.add_handler(CallbackQueryHandler(konkurslar_royxati, pattern=r"^ad_contest_list$"))



    app.add_handler(CallbackQueryHandler(InlineButton))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_manual_winner))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_admin_reply))

    # Schedule
    if app.job_queue:  # job_queue mavjudligini tekshiramiz
        # Birinchi yangilanishni boshlash
        app.job_queue.run_once(schedule_next_bio_update, 
                          when=datetime.now())
    
    # Bot start
    print("The bot is running!!")
    app.run_polling()
