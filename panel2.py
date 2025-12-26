import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from datetime import datetime
import sqlite3
from tistic6_6 import (
    load_latest_snapshot,
    generate_market_table_image,
    get_current_week_range,
    generate_weekly_report_image,
)
# ----------------  تایم گزارش لحظه‌ای ----------------
def get_last_snapshot_time():
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp FROM market_snapshots
        ORDER BY id DESC LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    return row[0] if row else "نامشخص"



BOT_TOKEN = "7835398677:AAG_aRC7OBGYRljfJb32d1SpLoYxghcApXk"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 👇 پنل شیشه‌ای ثابت (همیشه پایین چت می‌ماند)
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📊 گزارش لحظه‌ای"],
        ["📅 گزارش هفتگی"],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام — پنل فعال شد 👇\n\nیکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=MAIN_KEYBOARD
    )

# ---------------- کپشن ----------------
def format_instant_report(rows):
    lines = ["📊 گزارش لحظه‌ای بازار\n"]
    for r in rows:
        market, vol, val, buy_a, sell_a, power, flow = r
        emoji = "🟢" if float(flow.replace('B','').replace(',','')) >= 0 else "🔴"
        lines.append(
            f"{emoji} {market}\n"
            f"▪ ارزش: {val}\n"
            f"▪ قدرت خرید: {power}\n"
            f"▪ ورود/خروج پول: {flow}\n"
        )
    return "\n".join(lines)



# ---------------- 🟢 گزارش لحظه‌ای ----------------
async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rows = load_latest_snapshot()

        image_path = generate_market_table_image(rows)
        report_time = get_last_snapshot_time()
        caption_text = format_instant_report(rows)+ f"\n\n⏰ زمان گزارش: {report_time}"

        await update.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=caption_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("❌ خطا در تولید گزارش لحظه‌ای")


# ---------------- 🟢 گزارش هفتگی ----------------
async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start_date, end_date = get_current_week_range()

        image_path = generate_weekly_report_image(start_date, end_date)

        await update.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=f"📅 گزارش هفتگی\n{start_date} → {end_date}"
        )

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("❌ خطا در تولید گزارش هفتگی")


# ---------------- 🎮 کنترل ورودی‌های کاربر ----------------
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if text == "📊 گزارش لحظه‌ای":
        return await cmd_now(update, context)

    if text == "📅 گزارش هفتگی":
        return await cmd_weekly(update, context)

    await update.message.reply_text("از دکمه‌ها استفاده کن 🙂")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ربات غیرفعال شد.",
        reply_markup=ReplyKeyboardRemove()
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_router))

    print("UltronBot Panel is running…")
    app.run_polling()


if __name__ == "__main__":
    main()
