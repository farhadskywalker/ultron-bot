from playwright.sync_api import sync_playwright
import time
import requests
import sqlite3



BOT_TOKEN = "7835398677:AAG_aRC7OBGYRljfJb32d1SpLoYxghcApXk"
CHAT_ID = "-1003304858884"


def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )


def init_db():
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT,
    market_name TEXT,
    money_flow REAL,
    buy_power REAL
    )
    """)

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


def save_to_db(rows):
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime())

    for r in rows:
        if len(r) < 7:
            continue

        cur.execute("""
        INSERT INTO market_snapshots
        (timestamp, market_name, volume, value, buy_avg, sell_avg, buy_power, money_flow)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts,
            r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        ))

    conn.commit()
    conn.close()

def save_daily_report(rows):
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    today = time.strftime("%Y-%m-%d", time.localtime())

    # اگر امروز قبلاً ثبت شده، دوباره ثبت نکن
    cur.execute("SELECT 1 FROM daily_reports WHERE report_date = ? LIMIT 1", (today,))
    if cur.fetchone():
        conn.close()
        return

    for r in rows:
        try:
            market = r[0]
            buy_power = float(r[5].replace(",", ""))
            money_flow = float(r[6].replace(",", "").replace("B", ""))

            cur.execute("""
            INSERT INTO daily_reports (report_date, market_name, buy_power, money_flow)
            VALUES (?, ?, ?, ?)
            """, (today, market, buy_power, money_flow))
        except:
            continue

    conn.commit()
    conn.close()


def load_latest_snapshot():
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    # آخرین timestamp
    cur.execute("""
        SELECT timestamp
        FROM market_snapshots
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    last_ts = cur.fetchone()

    if not last_ts:
        conn.close()
        return []

    last_ts = last_ts[0]

    # همه ردیف‌های مربوط به آن زمان
    cur.execute("""
        SELECT market_name, volume, value, buy_avg, sell_avg, buy_power, money_flow
        FROM market_snapshots
        WHERE timestamp = ?
    """, (last_ts,))

    rows = cur.fetchall()
    conn.close()

    return rows

import datetime

def get_current_week_range():
    today = datetime.date.today()
    weekday = today.weekday()  
    # weekday: Monday=0 ... Sunday=6
    # شنبه در ایران = Monday در پایتون

    saturday = today - datetime.timedelta(days=weekday)
    wednesday = saturday + datetime.timedelta(days=4)

    return saturday.strftime("%Y-%m-%d"), wednesday.strftime("%Y-%m-%d")


def load_weekly_report():
    conn = sqlite3.connect("market_data.db")
    cur = conn.cursor()

    start, end = get_current_week_range()

    cur.execute("""
        SELECT
            market_name,
            SUM(money_flow) as total_money_flow,
            AVG(buy_power) as avg_buy_power
        FROM daily_reports
        WHERE report_date BETWEEN ? AND ?
        GROUP BY market_name
        ORDER BY total_money_flow DESC
    """, (start, end))

    rows = cur.fetchall()
    conn.close()
    return rows




def extract_table():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://tradersarena.ir/", timeout=90000)
        page.wait_for_selector("#marketDetails", timeout=90000)

        rows = page.query_selector_all("#marketDetailsBody tr")

        data = []

        for r in rows:
            cols = [c.inner_text().strip() for c in r.query_selector_all("td")]
            if cols:
                data.append(cols)

        browser.close()
        return data

import arabic_reshaper
from bidi.algorithm import get_display

def fix_fa(text):
    reshaped = arabic_reshaper.reshape(text)   # اتصال حروف
    bidi_text = get_display(reshaped)          # راست‌به‌چپ کردن
    return bidi_text



from PIL import Image, ImageDraw, ImageFont

def generate_market_table_image(rows):
    # تنظیمات
    width = 1400
    row_height = 80
    padding = 10
    header_bg = (185, 185, 185)
    positive_bg = (225, 255, 225)
    negative_bg = (255, 225, 225)
    text_color = (20, 20, 20)
    border_color = (200, 200, 200)

    # فونت‌ها
    font = ImageFont.truetype("IRANSansX-Regular.ttf", 24)
    font_bold = ImageFont.truetype("IRANSansX-Bold.ttf", 26)

    # ستون‌ها (از راست به چپ)
    headers = ["بازار", "حجم", "ارزش", "سرانه خرید", "سرانه فروش", "قدرت خرید", "ورود پول"]
    col_widths = [200, 160, 190, 190, 190, 160, 300]

    headers = list(reversed(headers))
    rows = [list(reversed(row)) for row in rows]

    total_width = sum(col_widths)
    height = padding * 2 + row_height * (len(rows) + 1)

    img = Image.new("RGB", (total_width + padding * 2, height), "white")
    draw = ImageDraw.Draw(img)

    # ==== هدر ====
    y = padding
    x = padding

    # پس‌زمینه هدر
    draw.rectangle([(x, y), (x + total_width, y + row_height)], fill=header_bg)

    cur_x = x
    for i, h in enumerate(headers):
        # راست‌چین + reshape
        h_fixed = get_display(arabic_reshaper.reshape(h))

        cell_w = col_widths[i]
        draw.text((cur_x + cell_w - 10, y + 25), h_fixed, fill=text_color, font=font_bold, anchor="ra")
        cur_x += cell_w

    # ==== داده‌ها ====
    y += row_height

    for row in rows:
        cur_x = x

        for i, cell in enumerate(row):
            bg_color = positive_bg 
                # index 0 = ورود پول , index 1 = قدرت خرید
            if i in [0, 1]:  
                    if cell.startswith("-"):
                        bg_color = negative_bg
                    else:
                        bg_color = positive_bg
            else:
                    bg_color = (230, 242, 255)   # آبی خیلی کمرنگ

            # بک‌گراند
            draw.rectangle([(cur_x, y), (cur_x + col_widths[i], y + row_height)], fill=bg_color)

            # متن راست‌چین
            fixed = get_display(arabic_reshaper.reshape(cell))
            draw.text(
                (cur_x + col_widths[i] - 10, y + 25),
                fixed,
                fill=text_color,
                font=font,
                anchor="ra"
            )

            # خط عمودی
            draw.line(
                [(cur_x + col_widths[i], y), (cur_x + col_widths[i], y + row_height)],
                fill=border_color,
                width=1
            )

            cur_x += col_widths[i]

        # خط افقی ردیف
        draw.line([(x, y + row_height), (x + total_width, y + row_height)], fill=border_color, width=1)

        y += row_height

    border_width = 25  # ضخامت کادر
    extra_bottom = 80  # مقدار فضای لازم برای متن پایین

    # ساخت تصویر نهایی بزرگتر
    final_width = img.width + border_width * 2
    final_height = img.height + border_width * 2 + extra_bottom

    final_img = Image.new("RGB", (final_width, final_height), "black")
    final_img.paste(img, (border_width, border_width))
    draw = ImageDraw.Draw(final_img)

    
    custom_text = "Produced by farhad [ultronbot]"
    text_x = border_width + 10
    text_y = border_width + img.height + 20   # درست زیر تصویر و روی پس‌زمینه سیاه

    draw.text((text_x, text_y), custom_text, fill=(255, 255, 255), font=font)

    final_img.save("market_summary.png", format="PNG")
    return "market_summary.png"





def format_report(rows):
    now = time.strftime("%Y/%m/%d - %H:%M", time.localtime())

    report = "📊 **خلاصه معاملات خرد و صندوق‌ها**\n\n"

    for row in rows:
        name = row[0] if len(row) > 0 else "-"
        vol = row[1] if len(row) > 1 else "-"
        val = row[2] if len(row) > 2 else "-"
        buy_avg = row[3] if len(row) > 3 else "-"
        sell_avg = row[4] if len(row) > 4 else "-"
        power = row[5] if len(row) > 5 else "-"
        money_in = row[6] if len(row) > 6 else "-"

        report += f"""
📌 **{name}**
▪ حجم معاملات: {vol}
▪ ارزش معاملات: {val}
▪ سرانه خرید: {buy_avg}
▪ سرانه فروش: {sell_avg}
▪ قدرت خرید: {power}
▪ ورود پول: {money_in}
""".strip() + "\n\n"

    report += f"⏱ زمان گزارش:\n{now}"
    return report

def format_weekly_report(rows, start_date, end_date):

    report = "📊 **گزارش هفتگی بازار (شنبه تا چهارشنبه)**\n\n"

    for r in rows:
        market, money, power = r


        emoji = "🟢" if money > 0 else "🔴"

        report += f"""
{emoji} **{market}**
▪ جمع ورود/خروج پول: {round(money, 1)} B
▪ میانگین قدرت خرید: {round(power, 2)}
▪ بازه گزارش: {start_date} → {end_date}


""".strip() + "\n\n"

    return report


def weekly_to_table_rows(weekly_data):
    rows = []

    for market, money, power in weekly_data:
        rows.append([
            market,
            "-",                 # حجم (هفتگی نداریم)
            "-",                 # ارزش
            "-",                 # سرانه خرید
            "-",                 # سرانه فروش
            f"{power:.2f}",      # قدرت خرید
            f"{money:.1f} B"     # ورود پول
        ])

    return rows

def generate_weekly_report_image(start_date, end_date):
    weekly = load_weekly_report()   # ✅ این خط اصلاح شد
    rows = weekly_to_table_rows(weekly)
    image_path = generate_market_table_image(rows)
    return image_path



if __name__ == "__main__":
    init_db()
    table = extract_table()   # 👈 دیتا تازه از سایت

    save_to_db(table)         # snapshot
    save_daily_report(table) # گزارش روزانه
    start_date, end_date = get_current_week_range()
    start_date = "2025-12-15"
    end_date = "2025-12-19"

    weekly_img = generate_weekly_report_image(start_date, end_date)
    with open(weekly_img, "rb") as f:
        requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={"chat_id": CHAT_ID},
        files={"photo": f}
    )


    weekly = load_weekly_report()
    print(format_weekly_report(weekly,start_date,end_date))

    msg = format_report(table)
    image_path = generate_market_table_image(table)
    daily_img = generate_market_table_image(table)

    with open(daily_img, "rb") as f:
        requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={"chat_id": CHAT_ID},
        files={"photo": f}
    )
# send(msg)
def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
    )

def send_photo(image_path, caption=None):
    with open(image_path, "rb") as img:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            files={"photo": img},
            data={
                "chat_id": CHAT_ID,
                "caption": caption or "",
                "parse_mode": "Markdown"
            }
        )

def handle_command(text):
    if text == "/now":
        table = extract_table()
        save_to_db(table)
        img = generate_market_table_image(table)
        send_photo(img, "📊 گزارش لحظه‌ای بازار")
        msg = format_report(table)
        send(msg)

    elif text == "/weekly":
        start, end = get_current_week_range()
        img = generate_weekly_report_image(start, end)
        send_photo(img, "📈 گزارش هفتگی بازار")

    elif text == "/help":
        send_message(
            "📌 دستورات ربات:\n"
            "/now - گزارش لحظه‌ای\n"
            "/weekly - گزارش هفتگی\n"
            "/monthly - گزارش ماهانه (به‌زودی)"
        )

def listen():
    offset = None
    while True:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30}
        ).json()

        for update in r.get("result", []):
            offset = update["update_id"] + 1

            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"].strip()
                handle_command(text)

if __name__ == "__main__":
    print("🤖 Bot is running and waiting for commands...")
    listen()

print("DONE")



