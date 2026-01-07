"""
tistic6_6.py
-----------------------------------
این فایل شامل:
✔ استخراج داده‌های جدول از سایت هدف
✔ ذخیره‌ی snapshot در دیتابیس
✔ ذخیره‌ی گزارش روزانه در دیتابیس
✔ ساخت تصویر و متن گزارش لحظه‌ای
✔ توابع فرمت‌سازی متن
✔ ارسال به تلگرام
"""

from playwright.sync_api import sync_playwright
import time
import requests
import sqlite3
import datetime

# 🟡 پیکربندی بات تلگرام
BOT_TOKEN = "7835398677:AAG_aRC7OBGYRljfJb32d1SpLoYxghcApXk"
CHAT_ID = "-1003304858884"

# ---------------------------------------------------------
# Helpers – توابع کمکی عمومی
# ---------------------------------------------------------

def send_text(msg: str):
    """ارسال پیام متن به تلگرام"""
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

# ---------------------------------------------------------
# Database – توابع دیتابیس
# ---------------------------------------------------------

def init_db():
    """ایجاد جداول مورد نیاز در دیتابیس در صورت نبودن"""
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    # جدول گزارش روزانه
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_date TEXT,
        market_name TEXT,
        money_flow REAL,
        buy_power REAL
    )
    """)

    # جدول snapshot از داده سایت
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        market_name TEXT,
        volume TEXT,
        value TEXT,
        buy_avg TEXT,
        sell_avg TEXT,
        buy_power TEXT,
        money_flow TEXT
    )
    """)

    conn.commit()
    conn.close()

def save_to_db(rows: list):
    """
    ذخیره‌ی snapshot در الجدول market_snapshots
    timestamp برای همه ردیف‌های یک snapshot یکی است
    """
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime())

    for row in rows:
        # اگر طول ردیف کمتر بود رد کن
        if len(row) < 7:
            continue

        cur.execute("""
        INSERT INTO market_snapshots (
            timestamp,
            market_name,
            volume,
            value,
            buy_avg,
            sell_avg,
            buy_power,
            money_flow
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts,
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6]
        ))

    conn.commit()
    conn.close()

def save_daily_report(rows: list):
    """
    ثبت گزارش روزانه در daily_reports
    یک بار در روز ذخیره می‌شود
    """
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    today = time.strftime("%Y-%m-%d", time.localtime())

    # اگر امروز قبلاً ثبت شده باشد، دوباره ذخیره نمی‌کند
    cur.execute(
        "SELECT 1 FROM daily_reports WHERE report_date = ? LIMIT 1",
        (today,)
    )
    if cur.fetchone():
        conn.close()
        return

    for r in rows:
        try:
            market = r[0]
            buy_power = float(r[5].replace(",", ""))
            money_flow = float(r[6].replace(",", "").replace("B", ""))
            cur.execute("""
            INSERT INTO daily_reports (
                report_date,
                market_name,
                buy_power,
                money_flow
            ) VALUES (?, ?, ?, ?)
            """, (today, market, buy_power, money_flow))
        except:
            continue

    conn.commit()
    conn.close()

def load_latest_snapshot() -> list:
    """بارگذاری آخرین snapshot ذخیره‌شده"""
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    # پیدا کردن آخرین timestamp
    cur.execute("""
    SELECT timestamp FROM market_snapshots
    ORDER BY timestamp DESC
    LIMIT 1
    """)
    last_ts = cur.fetchone()

    if not last_ts:
        conn.close()
        return []

    last_ts = last_ts[0]

    # بارگذاری همه ردیف‌های همان timestamp
    cur.execute("""
    SELECT market_name, volume, value, buy_avg, sell_avg, buy_power, money_flow
    FROM market_snapshots
    WHERE timestamp = ?
    """, (last_ts,))

    rows = cur.fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------
# توابع تاریخ
# ---------------------------------------------------------

def get_current_week_range():
    """
    بازه‌ی هفته جاری (شنبه تا چهارشنبه) را برمی‌گرداند
    """

    today = datetime.date.today()

    # تبدیل Python weekday → شنبه شروع هفته
    # Saturday = (weekday+2) % 7
    saturday = today - datetime.timedelta(days=(today.weekday()+2) % 7)
    wednesday = saturday + datetime.timedelta(days=4)

    return saturday.strftime("%Y-%m-%d"), wednesday.strftime("%Y-%m-%d")

def load_weekly_report() -> list:
    """
    گزارش هفتگی را از جدول daily_reports استخراج می‌کند
    """
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    start, end = get_current_week_range()

    cur.execute("""
    SELECT market_name,
           SUM(money_flow) AS total_money_flow,
           AVG(buy_power)  AS avg_buy_power
    FROM daily_reports
    WHERE report_date BETWEEN ? AND ?
    GROUP BY market_name
    ORDER BY total_money_flow DESC
    """, (start, end))

    rows = cur.fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------
# استخراج جدول از سایت
# ---------------------------------------------------------

def extract_table() -> list:
    """
    با Playwright صفحه را باز می‌کند،
    داده‌های جدول را می‌خواند و بازمی‌گرداند
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://tradersarena.ir/", timeout=90000)
        page.wait_for_selector("#marketDetails", timeout=90000)

        rows = page.query_selector_all("#marketDetailsBody tr")
        data = []

        for r in rows:
            cols = [c.inner_text().strip()
                    for c in r.query_selector_all("td")]
            if cols:
                data.append(cols)

        browser.close()
        return data

# ---------------------------------------------------------
# راست‌چین و فارسی‌سازی
# ---------------------------------------------------------

import arabic_reshaper
from bidi.algorithm import get_display

def fix_fa(text: str) -> str:
    """
    فارسی کردن متن با پشتیبانی از RTL
    """
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    return bidi_text

# ---------------------------------------------------------
# گزارش تصویری (گزارش لحظه‌ای)
# ---------------------------------------------------------

from PIL import Image, ImageDraw, ImageFont, ImageOps

def generate_market_table_image(rows: list) -> str:
    """
    خروجی تصویر جدول لحظه‌ای بازار
    (شامل رنگ‌های مثبت/منفی + RTL + فونت استاندارد)
    """

    # تنظیمات
    width = 1400
    row_h = 80
    padding = 10
    header_bg = (185, 185, 185)
    positive_bg = (225, 255, 225)
    negative_bg = (255, 225, 225)
    text_color = (20, 20, 20)
    border_color = (200, 200, 200)

    # فونت‌ها
    font = ImageFont.truetype("IRANSansX-Regular.ttf", 24)
    font_b = ImageFont.truetype("IRANSansX-Bold.ttf", 26)

    # ترتیب ستون‌ها از راست به چپ
    headers = [
        "بازار", "حجم", "ارزش", "سرانه خرید",
        "سرانه فروش", "قدرت خرید", "ورود پول"
    ]

    # جابجایی برای راست‌به‌چپ
    headers = list(reversed(headers))
    rows = [list(reversed(r)) for r in rows]

    # پهنا هر ستون
    col_widths = [200, 160, 190, 190, 190, 160, 300]
    total_w = sum(col_widths)

    # اندازه تصویر
    height = padding*2 + row_h*(len(rows)+1)
    img = Image.new("RGB", (total_w + padding*2, height), "white")
    draw = ImageDraw.Draw(img)

    # رسم هدر جدول
    y = padding
    draw.rectangle([(padding, y), (padding+total_w, y+row_h)],
                   fill=header_bg)

    x = padding
    for i, h in enumerate(headers):
        text = fix_fa(h)
        draw.text((x + col_widths[i] - 10, y+25),
                  text, fill=text_color, font=font_b,
                  anchor="ra")
        draw.line([(x+col_widths[i], y),
                   (x+col_widths[i], y+row_h)],
                  fill=border_color, width=1)
        x += col_widths[i]

    # رسم داده‌ها
    y += row_h
    for r in rows:
        x = padding
        for i, cell in enumerate(r):

            # رنگ پس‌زمینه
            if i in (0, 1):  # قدرت خرید & ورود پول
                # اگر منفی
                if cell.startswith("-"):
                    bg = negative_bg
                else:
                    bg = positive_bg
            else:
                bg = (230, 242, 255)  # آبی خیلی کمرنگ

            draw.rectangle([(x, y), (x+col_widths[i], y+row_h)],
                           fill=bg)

            text = fix_fa(cell)
            draw.text((x+col_widths[i]-10, y+25),
                      text, fill=text_color, font=font,
                      anchor="ra")

            # خطوط
            draw.line([(x+col_widths[i], y),
                       (x+col_widths[i], y+row_h)],
                      fill=border_color, width=1)

            x += col_widths[i]

        # خط افقی
        draw.line([(padding, y+row_h),
                   (padding+total_w, y+row_h)],
                  fill=border_color, width=1)
        y += row_h

    # ذخیره نهایی با کادر سیاه
    final = ImageOps.expand(img, border=25, fill="black")

    # دوباره ابزار draw روی تصویر نهایی
    draw = ImageDraw.Draw(final)

    # متن پایین (زمان گزارش)
    now = time.strftime("%Y/%m/%d - %H:%M", time.localtime())
    foot = f"Produced by farhad [ultronbot] ⏱ report time: {now}"

    # موقعیت متن (کمی فاصله از پایین)
    draw.text(
        (25, final.height - 28),
        foot,
        fill=(255, 255, 255),
        font=font_b
    )

    path = "market_summary.png"
    final.save(path, format="PNG")
    return path


if __name__ == "__main__":
    init_db()

    print("در حال گرفتن داده از سایت...")
    rows = extract_table()

    save_to_db(rows)
    save_daily_report(rows)

    img = generate_market_table_image(rows)
    print("Saved:", img)
