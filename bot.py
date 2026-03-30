#!/usr/bin/env python3
"""
🇪🇸 بوت Telegram لمراقبة مواعيد ICP الإسبانية
"""

import os
import time
import random
import asyncio
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ─── إعدادات ───────────────────────────────────────────
BOT_TOKEN  = "8738876627:AAECtkMR8plQbsL_uOKEqOMNE47oSPRbWvk"   # من Railway Environment Variables
ADMIN_ID   = 1026183307  # Chat ID بتاعك

TARGET_URL = "https://icp.administracionelectronica.gob.es/icpplustieb/volverPortada"

NO_APPOINTMENT_TEXTS = [
    "en este momento no hay citas disponibles",
    "no hay citas",
    "no existen citas",
    "no quedan citas",
]

CHECK_INTERVAL_MIN = 40   # ثانية
CHECK_INTERVAL_MAX = 80   # ثانية

# ─── logging ───────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ─── State ─────────────────────────────────────────────
monitoring = False
check_count = 0
last_check_time = None
monitor_task = None

# ─── فحص الموقع ────────────────────────────────────────
def check_website() -> tuple[bool | None, str]:
    """
    True  = يمكن في موعد
    False = مفيش مواعيد
    None  = خطأ
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        r = requests.get(TARGET_URL, headers=headers, timeout=20)
        page = r.text.lower()
        for txt in NO_APPOINTMENT_TEXTS:
            if txt in page:
                return False, "مفيش مواعيد دلوقتي"
        return True, "🎉 يمكن ظهر موعد!"
    except Exception as e:
        return None, f"خطأ في الاتصال: {e}"

# ─── حلقة المراقبة ─────────────────────────────────────
async def monitoring_loop(app: Application):
    global monitoring, check_count, last_check_time
    log.info("بدأت المراقبة")

    while monitoring:
        check_count += 1
        last_check_time = datetime.now().strftime("%H:%M:%S")
        log.info(f"فحص #{check_count}")

        result, msg = check_website()

        if result is True:
            log.warning("⚠️ يمكن في موعد!")
            keyboard = [[InlineKeyboardButton("🔗 افتح الموقع فوراً", url=TARGET_URL)]]
            await app.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🚨🚨🚨 <b>ظهر موعد!</b> 🚨🚨🚨\n\n"
                    "افتح الموقع دلوقتي فوراً قبل ما يتاخد! 👇"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            # فضل يراقب بعد كده
            await asyncio.sleep(30)

        elif result is False:
            log.info(f"❌ {msg}")

        else:
            log.error(f"⚠️ {msg}")

        if not monitoring:
            break

        wait = random.randint(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
        log.info(f"هينتظر {wait} ثانية...")
        await asyncio.sleep(wait)

    log.info("وقفت المراقبة")

# ─── Commands ──────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [
            InlineKeyboardButton("▶️ ابدأ المراقبة", callback_data="start_mon"),
            InlineKeyboardButton("⏹ وقف", callback_data="stop_mon"),
        ],
        [InlineKeyboardButton("📊 الحالة", callback_data="status")],
        [InlineKeyboardButton("🔍 فحص الآن", callback_data="check_now")],
    ]
    await update.message.reply_text(
        "👋 <b>أهلاً! أنا بوت مراقبة مواعيد ICP</b>\n\n"
        "براقب الموقع الإسباني وأبعتلك إشعار فوري لما يظهر موعد 🇪🇸\n\n"
        "اختار أمر من الأزرار:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "📋 <b>الأوامر المتاحة:</b>\n\n"
        "/start — القائمة الرئيسية\n"
        "/startmon — ابدأ المراقبة\n"
        "/stopmon — وقف المراقبة\n"
        "/status — الحالة الحالية\n"
        "/checknow — فحص فوري\n"
        "/help — المساعدة",
        parse_mode="HTML",
    )

async def cmd_startmon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    global monitoring, monitor_task, check_count
    if monitoring:
        await update.message.reply_text("⚠️ المراقبة شغّالة بالفعل!")
        return
    monitoring = True
    check_count = 0
    monitor_task = asyncio.create_task(monitoring_loop(ctx.application))
    await update.message.reply_text(
        f"✅ <b>بدأت المراقبة!</b>\n\n"
        f"⏱ هفحص كل {CHECK_INTERVAL_MIN}-{CHECK_INTERVAL_MAX} ثانية\n"
        f"🔗 {TARGET_URL}\n\n"
        f"هبعتلك رسالة فوراً لما يظهر موعد 🔔",
        parse_mode="HTML",
    )

async def cmd_stopmon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    global monitoring, monitor_task
    if not monitoring:
        await update.message.reply_text("⚠️ المراقبة مش شغّالة أصلاً!")
        return
    monitoring = False
    if monitor_task:
        monitor_task.cancel()
        monitor_task = None
    await update.message.reply_text("⏹ <b>وقفت المراقبة.</b>", parse_mode="HTML")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    status = "🟢 شغّالة" if monitoring else "🔴 واقفة"
    await update.message.reply_text(
        f"📊 <b>الحالة:</b>\n\n"
        f"المراقبة: {status}\n"
        f"عدد الفحوصات: {check_count}\n"
        f"آخر فحص: {last_check_time or 'لسه متبدأتش'}\n"
        f"الموقع: {TARGET_URL}",
        parse_mode="HTML",
    )

async def cmd_checknow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = await update.message.reply_text("🔍 بفحص دلوقتي...")
    result, text = check_website()
    emoji = "🎉" if result is True else ("❌" if result is False else "⚠️")
    keyboard = [[InlineKeyboardButton("🔗 افتح الموقع", url=TARGET_URL)]]
    await msg.edit_text(
        f"{emoji} <b>نتيجة الفحص:</b>\n\n{text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ─── Callbacks (الأزرار) ────────────────────────────────
async def button_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "start_mon":
        await cmd_startmon.__wrapped__(update, ctx) if hasattr(cmd_startmon, '__wrapped__') else None
        global monitoring, monitor_task, check_count
        if monitoring:
            await q.edit_message_text("⚠️ المراقبة شغّالة بالفعل!")
            return
        monitoring = True
        check_count = 0
        monitor_task = asyncio.create_task(monitoring_loop(ctx.application))
        await q.edit_message_text(
            f"✅ <b>بدأت المراقبة!</b>\n\n"
            f"⏱ هفحص كل {CHECK_INTERVAL_MIN}-{CHECK_INTERVAL_MAX} ثانية\n"
            f"هبعتلك رسالة فوراً لما يظهر موعد 🔔",
            parse_mode="HTML",
        )

    elif data == "stop_mon":
        if not monitoring:
            await q.edit_message_text("⚠️ المراقبة مش شغّالة أصلاً!")
            return
        monitoring = False
        if monitor_task:
            monitor_task.cancel()
        await q.edit_message_text("⏹ <b>وقفت المراقبة.</b>", parse_mode="HTML")

    elif data == "status":
        status = "🟢 شغّالة" if monitoring else "🔴 واقفة"
        await q.edit_message_text(
            f"📊 <b>الحالة:</b>\n\n"
            f"المراقبة: {status}\n"
            f"عدد الفحوصات: {check_count}\n"
            f"آخر فحص: {last_check_time or 'لسه متبدأتش'}",
            parse_mode="HTML",
        )

    elif data == "check_now":
        await q.edit_message_text("🔍 بفحص دلوقتي...")
        result, text = check_website()
        emoji = "🎉" if result is True else ("❌" if result is False else "⚠️")
        keyboard = [[InlineKeyboardButton("🔗 افتح الموقع", url=TARGET_URL)]]
        await q.edit_message_text(
            f"{emoji} <b>نتيجة الفحص:</b>\n\n{text}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

# ─── Main ───────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("startmon", cmd_startmon))
    app.add_handler(CommandHandler("stopmon",  cmd_stopmon))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("checknow", cmd_checknow))
    app.add_handler(CallbackQueryHandler(button_callback))

    log.info("البوت شغّال ✅")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
