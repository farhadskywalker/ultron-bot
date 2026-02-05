import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- توابعی که از tisticnow می‌گیریم ---
from tisticnow import (
    extract_table,
    save_to_db,
    save_daily_report,
    generate_market_table_image   
)

# --- از فایل گزارش هفتگی ---
from tistic_weekly_full2 import (
    build_week_table,
    generate_weekly_report_image,
)

BOT_TOKEN = "7835398677:AAG_aRC7OBGYRljfJb32d1SpLoYxghcApXk"


# =========================
# /start  ➜ نمایش پنل شیشه‌ای
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ["📊 گزارش لحظه‌ای", "📆 گزارش هفتگی"]
    ]

    await update.message.reply_text(
        "🔹 یکی از گزینه‌ها را انتخاب کن:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )


# =========================
# 📊 گزارش لحظه‌ای
# =========================
async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = await update.message.reply_text("⏳ در حال ساخت گزارش لحظه‌ای...")

    try:
        rows = await asyncio.to_thread(extract_table)

        save_to_db(rows)
        save_daily_report(rows)

        # کپشن را اینجا می‌سازیم
        caption_lines = ["📊 گزارش لحظه‌ای بازار\n"]

        for r in rows:
            market, vol, val, buy_a, sell_a, power, flow = r
            emoji = "🟢" if float(flow.replace("B","").replace(",","")) >= 0 else "🔴"

            caption_lines.append(
                f"{emoji} {market}\n"
                f"▪ ارزش: {val}\n"
                f"▪ قدرت خرید: {power}\n"
                f"▪ ورود/خروج پول: {flow}\n"
            )

        caption = "\n".join(caption_lines)

        image_path = generate_market_table_image(rows)

        await update.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=caption
        )

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ خطا در اجرای گزارش لحظه‌ای:\n{e}")


# =========================
# 📆 گزارش هفتگی
# =========================
async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = await update.message.reply_text("⏳ در حال ساخت گزارش هفتگی...")

    try:
        weekly_rows, start_date, end_date = build_week_table()

        image_path = generate_weekly_report_image(
            weekly_rows,
            start_date,
            end_date
        )

        await update.message.reply_photo(
            photo=open(image_path, "rb"),
            caption=f"📆 گزارش هفتگی ({start_date} → {end_date})"
        )

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ خطا در اجرای گزارش هفتگی:\n{e}")


# =========================
# هندلر متن → دکمه‌ها
# =========================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📊 گزارش لحظه‌ای":
        await cmd_now(update, context)

    elif text == "📆 گزارش هفتگی":
        await cmd_weekly(update, context)


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))

    print("UltronBot Panel is running…")
    app.run_polling()


if __name__ == "__main__":
    main()
