from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CallbackQueryHandler,
    MessageHandler, CommandHandler, filters, ContextTypes
)
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from django.utils import timezone
from ..decorators import admin_required
from ..models.Konkurs import Contest, ContestCondition

# Bosqichlar
TITLE, DESCRIPTION, START_DATE, END_DATE, CONDITIONS, CONDITION_VALUE, REVIEW = range(7)

# ========= UTILS =========

def chunk_buttons(buttons, cols=3):
    """Buttonlarni cols ustun bo‘lib bo‘lib qaytaradi: List[List[InlineKeyboardButton]]"""
    rows, row = [], []
    for i, b in enumerate(buttons, start=1):
        row.append(b)
        if i % cols == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows

def ikm(rows):
    """List[List[InlineKeyboardButton]] -> InlineKeyboardMarkup"""
    return InlineKeyboardMarkup(rows)

def as_aware(dt: datetime) -> datetime:
    """Ensure timezone-aware datetime in current timezone."""
    if timezone.is_aware(dt):
        return dt.astimezone(timezone.get_current_timezone())
    return timezone.make_aware(dt, timezone.get_current_timezone())

# ========= START =========

@admin_required
async def start_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Draft contest yaratamiz
    now = timezone.now()
    contest = await sync_to_async(Contest.objects.create)(
        title="Draft",
        description="",
        start_date=now,   # vaqtinchalik, keyin yangilanadi
        end_date=now,     # vaqtinchalik, keyin yangilanadi
        is_active=False,
    )
    context.user_data.clear()
    context.user_data["contest_id"] = contest.id
    context.user_data["time_select"] = {"start": {}, "end": {}}

    await update.callback_query.edit_message_text("📝 Konkurs nomini kiriting:")
    return TITLE

# ========= TITLE =========

async def contest_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contest = await sync_to_async(Contest.objects.get)(id=context.user_data["contest_id"])
    title = (update.message.text or "").strip()

    if len(title) < 3:
        await update.message.reply_text("❌ Konkurs nomi juda qisqa. Qaytadan kiriting:")
        return TITLE

    contest.title = title
    await sync_to_async(contest.save)()
    await update.message.reply_text("📄 Konkurs tavsifini kiriting:")
    return DESCRIPTION

# ========= DESCRIPTION & START PRESETS =========

async def contest_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contest = await sync_to_async(Contest.objects.get)(id=context.user_data["contest_id"])
    desc = (update.message.text or "").strip()
    contest.description = desc
    await sync_to_async(contest.save)()

    # Boshlanish vaqtini tanlash: +1/+2/+3/+5 soat, +1 kun, Custom (5 kun)
    rows = chunk_buttons([
        InlineKeyboardButton("⏱ +1 soat", callback_data="s_preset_hour_1"),
        InlineKeyboardButton("⏱ +2 soat", callback_data="s_preset_hour_2"),
        InlineKeyboardButton("⏱ +3 soat", callback_data="s_preset_hour_3"),
        InlineKeyboardButton("⏱ +5 soat", callback_data="s_preset_hour_5"),
        InlineKeyboardButton("📅 +1 kun",  callback_data="s_preset_day_1"),
        InlineKeyboardButton("✏️ Custom (5 kun)", callback_data="s_custom_5days"),
    ], cols=3)

    await update.message.reply_text(
        "⏰ Konkurs boshlanish vaqtini tanlang:",
        reply_markup=ikm(rows)
    )
    return START_DATE

# ========= START DATE CALLBACKS =========

async def contest_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    ts = context.user_data.setdefault("time_select", {"start": {}, "end": {}})
    now = timezone.now().replace(second=0, microsecond=0)
    min_start = now + timedelta(hours=1)  # minimal +1 soat

    # ---- Preset: +N hours ----
    if data.startswith("s_preset_hour_"):
        hrs = int(data.split("_")[-1])
        candidate = now + timedelta(hours=hrs)
        # minimal qoida
        if candidate < min_start:
            candidate = min_start
        # :00 ga tekislash
        candidate = candidate.replace(minute=0)
        ts["start"]["final_dt"] = candidate
        return await _show_minute_options_for_start(query, candidate)

    # ---- Preset: +1 day ----
    if data.startswith("s_preset_day_"):
        days = int(data.split("_")[-1])
        choose_date = (now + timedelta(days=days)).date()
        ts["start"]["candidate_date"] = choose_date
        return await _show_hour_options_for_start(query, choose_date)

    # ---- Custom (5 days) -> choose day ----
    if data == "s_custom_5days":
        base = (now + timedelta(days=1)).date()
        day_buttons = [InlineKeyboardButton((base + timedelta(days=i)).strftime("%d %b"),
                                            callback_data=f"s_day_{(base + timedelta(days=i)).isoformat()}")
                       for i in range(5)]
        rows = chunk_buttons(day_buttons, cols=3)
        rows.append([InlineKeyboardButton("❌ Bekor", callback_data="s_cancel")])
        await query.edit_message_text("📅 Kun tanlang:", reply_markup=ikm(rows))
        return START_DATE

    # ---- Day chosen -> choose hour ----
    if data.startswith("s_day_"):
        chosen_date = datetime.fromisoformat(data.split("_", 2)[2]).date()
        ts["start"]["candidate_date"] = chosen_date
        return await _show_hour_options_for_start(query, chosen_date)

    # ---- Hour chosen -> choose minute ----
    if data.startswith("s_hour_"):
        hour = int(data.split("_")[-1])
        chosen_date = ts["start"].get("candidate_date")
        if not chosen_date:
            await query.edit_message_text("❌ Avval kunni tanlang.")
            return START_DATE
        chosen_dt = datetime.combine(chosen_date, datetime.min.time()).replace(hour=hour, minute=0)
        chosen_dt = as_aware(chosen_dt)
        ts["start"]["final_dt"] = chosen_dt
        return await _show_minute_options_for_start(query, chosen_dt)

    # ---- Minute chosen (00,10,15,20,25) ----
    if data.startswith("s_min_"):
        minute = int(data.split("_")[-1])
        current_dt = ts["start"].get("final_dt")
        if not current_dt:
            await query.edit_message_text("❌ Avval soatni tanlang.")
            return START_DATE
        ts["start"]["final_dt"] = current_dt.replace(minute=minute)
        return await _show_minute_options_for_start(query, ts["start"]["final_dt"])

    # ---- Save start time ----
    if data == "s_save":
        final = ts["start"].get("final_dt")
        if not final or final < min_start:
            final = min_start
        # Save to DB
        contest = await sync_to_async(Contest.objects.get)(id=context.user_data["contest_id"])
        contest.start_date = final
        await sync_to_async(contest.save)()
        await query.edit_message_text(f"⏱ Boshlanish vaqti saqlandi: {final.strftime('%Y-%m-%d %H:%M')}")
        # Proceed to end date selection
        return await _prompt_end_date_selection(query)

    if data == "s_cancel":
        await query.edit_message_text("❌ Boshlanish tanlovi bekor qilindi.")
        return START_DATE

    await query.edit_message_text("❌ Noma'lum amal.")
    return START_DATE

async def _show_hour_options_for_start(query, chosen_date):
    # 24 soatni 3 ustundan chiqazamiz
    btns = [InlineKeyboardButton(f"{h:02d}:00", callback_data=f"s_hour_{h}") for h in range(24)]
    rows = chunk_buttons(btns, cols=3)
    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="s_custom_5days")])
    await query.edit_message_text("🕐 Boshlanish soatini tanlang:", reply_markup=ikm(rows))
    return START_DATE

async def _show_minute_options_for_start(query, base_dt):
    # 00,10,15,20,25 + Saqlash (yuqori va pastda)
    hour = base_dt.strftime("%H")
    min_buttons = [
        InlineKeyboardButton(f"{hour}:00", callback_data="s_min_0"),
        InlineKeyboardButton(f"{hour}:10", callback_data="s_min_10"),
        InlineKeyboardButton(f"{hour}:15", callback_data="s_min_15"),
        InlineKeyboardButton(f"{hour}:20", callback_data="s_min_20"),
        InlineKeyboardButton(f"{hour}:25", callback_data="s_min_25"),
    ]
    rows = [[InlineKeyboardButton("💾 Saqlash", callback_data="s_save")]]  # TOP save
    rows += chunk_buttons(min_buttons, cols=3)
    rows.append([InlineKeyboardButton("💾 Saqlash", callback_data="s_save")])  # BOTTOM save
    await query.edit_message_text("⏱ Boshlanish daqiqasini tanlang:", reply_markup=ikm(rows))
    return START_DATE

# ========= END DATE (31 days) =========

async def _prompt_end_date_selection(query):
    now = timezone.now()
    start_day = (now + timedelta(days=1)).date()
    day_buttons = [
        InlineKeyboardButton((start_day + timedelta(days=i)).strftime("%d %b"),
                             callback_data=f"e_day_{(start_day + timedelta(days=i)).isoformat()}")
        for i in range(31)
    ]
    rows = chunk_buttons(day_buttons, cols=3)
    rows.append([InlineKeyboardButton("❌ Bekor", callback_data="e_cancel")])
    await query.edit_message_text("📅 Tugash kunini tanlang (1–31 kun oralig‘ida):", reply_markup=ikm(rows))
    return END_DATE

async def contest_end_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    ts = context.user_data.setdefault("time_select", {"start": {}, "end": {}})

    if data.startswith("e_day_"):
        chosen_date = datetime.fromisoformat(data.split("_", 2)[2]).date()
        ts["end"]["candidate_date"] = chosen_date
        return await _show_hour_options_for_end(query, chosen_date)

    if data.startswith("e_hour_"):
        hour = int(data.split("_")[-1])
        if not ts["end"].get("candidate_date"):
            await query.edit_message_text("❌ Avval tugash kunini tanlang.")
            return END_DATE
        base_dt = datetime.combine(ts["end"]["candidate_date"], datetime.min.time()).replace(hour=hour, minute=0)
        base_dt = as_aware(base_dt)
        ts["end"]["final_dt"] = base_dt
        return await _show_minute_options_for_end(query, base_dt)

    if data.startswith("e_min_"):
        minute = int(data.split("_")[-1])
        base_dt = ts["end"].get("final_dt")
        if not base_dt:
            await query.edit_message_text("❌ Avval soatni tanlang.")
            return END_DATE
        ts["end"]["final_dt"] = base_dt.replace(minute=minute)
        return await _show_minute_options_for_end(query, ts["end"]["final_dt"])

    if data == "e_save":
        final = ts["end"].get("final_dt")
        contest = await sync_to_async(Contest.objects.get)(id=context.user_data["contest_id"])
        if not final or final <= contest.start_date:
            await query.edit_message_text("❌ Tugash vaqti boshlangan vaqtdan keyin bo‘lishi shart. Qayta tanlang.")
            return END_DATE
        contest.end_date = final
        await sync_to_async(contest.save)()
        await query.edit_message_text(f"✅ Tugash vaqti saqlandi: {final.strftime('%Y-%m-%d %H:%M')}")
        return await _prompt_conditions_after_end(query)

    if data == "e_cancel":
        await query.edit_message_text("❌ Tugash vaqti tanlovi bekor qilindi.")
        return END_DATE

    await query.edit_message_text("❌ Noma'lum amal.")
    return END_DATE

async def _show_hour_options_for_end(query, chosen_date):
    btns = [InlineKeyboardButton(f"{h:02d}:00", callback_data=f"e_hour_{h}") for h in range(24)]
    rows = chunk_buttons(btns, cols=3)
    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="e_cancel")])
    await query.edit_message_text("🕐 Tugash soatini tanlang:", reply_markup=ikm(rows))
    return END_DATE

async def _show_minute_options_for_end(query, base_dt):
    hour = base_dt.strftime("%H")
    min_buttons = [
        InlineKeyboardButton(f"{hour}:00", callback_data="e_min_0"),
        InlineKeyboardButton(f"{hour}:10", callback_data="e_min_10"),
        InlineKeyboardButton(f"{hour}:15", callback_data="e_min_15"),
        InlineKeyboardButton(f"{hour}:20", callback_data="e_min_20"),
        InlineKeyboardButton(f"{hour}:25", callback_data="e_min_25"),
    ]
    rows = [[InlineKeyboardButton("💾 Saqlash", callback_data="e_save")]]  # TOP save
    rows += chunk_buttons(min_buttons, cols=3)
    rows.append([InlineKeyboardButton("💾 Saqlash", callback_data="e_save")])  # BOTTOM save
    await query.edit_message_text("⏱ Tugash daqiqasini tanlang:", reply_markup=ikm(rows))
    return END_DATE

# ========= CONDITIONS =========

async def _prompt_conditions_after_end(query):
    # Shartlarni tanlash ekrani
    rows = [
        [InlineKeyboardButton("📢 Kanalga obuna", callback_data="subscribe_channel")],
        [InlineKeyboardButton("👥 Foydalanuvchi taklif qilish", callback_data="invite_users")],
        [InlineKeyboardButton("🤖 Botga /start bosish", callback_data="bot_start")],
        [InlineKeyboardButton("📝 Saytda ro‘yxatdan o‘tish", callback_data="site_register")],
        [InlineKeyboardButton("🔥 Saytda faol bo‘lish", callback_data="site_activity")],
        [InlineKeyboardButton("✅ Yakunlash", callback_data="done")],
    ]
    await query.edit_message_text("📌 Shartlarni tanlang (keragicha qo‘shing):", reply_markup=ikm(rows))
    return CONDITIONS

async def contest_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    condition = query.data
    await query.answer()

    contest = await sync_to_async(Contest.objects.get)(id=context.user_data["contest_id"])

    # 🔥 Agar "yana shart qo‘shish" bosilsa
    if condition == "back_conditions":
        return await _prompt_conditions_after_end(query)

    if condition == "done":
        return await show_review(query, contest)

    # Yangi shartni draft holatda yaratamiz
    cond = await sync_to_async(ContestCondition.objects.create)(
        contest=contest,
        condition_type=condition,
        value="",
        is_required=True,
    )
    context.user_data["current_condition_id"] = cond.id

    prompts = {
        "subscribe_channel": "📢 Kanal(lar)ni yuboring (masalan: @kanal1, @kanal2 yoki t.me/kanal):",
        "invite_users": "👥 Nechta foydalanuvchi taklif qilishi kerak? (faqat raqam):",
        "bot_start": "🤖 Bot username ni yuboring (@username):",
        "site_register": "📝 Sayt havolasini yuboring (https://...):",
        "site_activity": "🔥 Necha kun faol bo‘lishi kerak? (faqat raqam):",
    }
    await query.edit_message_text(prompts.get(condition, "Qiymatni yuboring:"))
    return CONDITION_VALUE



async def contest_condition_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    cond = await sync_to_async(ContestCondition.objects.get)(id=context.user_data["current_condition_id"])

    # Validatsiya
    if cond.condition_type in ["invite_users", "site_activity"]:
        if not text.isdigit():
            await update.message.reply_text("❌ Iltimos faqat raqam kiriting.")
            return CONDITION_VALUE
    elif cond.condition_type == "bot_start":
        if not (text.startswith("@") and len(text) > 1):
            await update.message.reply_text("❌ Bot username noto‘g‘ri. Masalan: @MyBot")
            return CONDITION_VALUE
    elif cond.condition_type in ["subscribe_channel", "site_register"]:
        if len(text) < 3:
            await update.message.reply_text("❌ Qiymat juda qisqa. Qayta kiriting.")
            return CONDITION_VALUE

    cond.value = text
    await sync_to_async(cond.save)()

    # Majburiy/ixtiyoriy tanlash
    keyboard = ikm([
        [
            InlineKeyboardButton("✅ Majburiy", callback_data=f"cond_req_{cond.id}_1"),
            InlineKeyboardButton("⚪ Ixtiyoriy", callback_data=f"cond_req_{cond.id}_0"),
        ],
        [InlineKeyboardButton("➕ Yana shart qo‘shish", callback_data="back_conditions")],
        [InlineKeyboardButton("✅ Yakunlash", callback_data="done")],
    ])
    await update.message.reply_text(
        f"Shart qo‘shildi: {cond.get_condition_type_display()} → {cond.value}\n"
        f"Majburiyligini tanlang yoki davom eting:",
        reply_markup=keyboard
    )
    return CONDITIONS

async def contest_condition_required(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, cond_id, flag = query.data.split("_")
    cond = await sync_to_async(ContestCondition.objects.get)(id=int(cond_id))
    cond.is_required = bool(int(flag))
    await sync_to_async(cond.save)()
    await query.answer("✅ Shart yangilandi.")
    # Shartlar menyusiga qaytaramiz
    return await _prompt_conditions_after_end(query)

# ========= REVIEW =========

async def show_review(query, contest: Contest):
    conditions = await sync_to_async(list)(contest.conditions.all())
    cond_text = "\n".join(
        f"• {c.get_condition_type_display()} → {c.value} "
        f"({'Majburiy' if c.is_required else 'Ixtiyoriy'})" for c in conditions
    ) or "Shart yo‘q"

    text = (
        f"📋 <b>Konkurs ma’lumotlari:</b>\n\n"
        f"📌 Nomi: {contest.title}\n"
        f"📄 Tavsif: {contest.description}\n"
        f"⏰ Boshlanish: {contest.start_date}\n"
        f"⏰ Tugash: {contest.end_date}\n"
        f"✅ Shartlar:\n{cond_text}\n\n"
        f"Saqlash yoki bekor qilishni tanlang:"
    )
    keyboard = ikm([
        [InlineKeyboardButton("💾 Saqlash", callback_data="save")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    return REVIEW

async def contest_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    await query.answer()
    contest = await sync_to_async(Contest.objects.get)(id=context.user_data["contest_id"])

    if action == "save":
        contest.is_active = True
        await sync_to_async(contest.save)()
        await query.edit_message_text("✅ Konkurs saqlandi va faollashtirildi!")
    else:
        await query.edit_message_text("❌ Konkurs bekor qilindi. Draft sifatida qoldi.")
    return ConversationHandler.END

# ========= CANCEL =========

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Konkurs yaratish bekor qilindi. Draft sifatida saqlanib qoladi.")
    return ConversationHandler.END

# ========= CONVERSATION HANDLER =========

Conkurs_Conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_contest, pattern=r"^create_contest$")],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, contest_title)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, contest_description)],
        START_DATE: [CallbackQueryHandler(contest_start_callback, pattern=r"^s_")],
        END_DATE: [CallbackQueryHandler(contest_end_callback, pattern=r"^e_")],
        CONDITIONS: [
            CallbackQueryHandler(contest_conditions, pattern=r"^(subscribe_channel|invite_users|bot_start|site_register|site_activity|done|back_conditions)$"),
            CallbackQueryHandler(contest_condition_required, pattern=r"^cond_req_"),
        ],
        CONDITION_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, contest_condition_value)],
        REVIEW: [CallbackQueryHandler(contest_review, pattern=r"^(save|cancel)$")],
    },
    fallbacks=[MessageHandler(filters.COMMAND, cancel)],
    allow_reentry=True,
)
