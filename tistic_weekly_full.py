# tistic – weekly image + db (with Jalali dates using jdatetime)

import sqlite3
import datetime
import jdatetime
from PIL import Image, ImageDraw, ImageFont

DB = "market_data.db"
FONT = "IRANSansX-Regular.ttf"
FONT_BOLD = "IRANSansX-Bold.ttf"

# ---------------------
# Helpers
# ---------------------

def to_jalali(date_iso: str) -> str:
    y, m, d = map(int, date_iso.split("-"))
    j = jdatetime.date.fromgregorian(year=y, month=m, day=d)
    return j.strftime("%Y/%m/%d")


def get_week_range():
    today = datetime.date.today()
    # بورس ایران: شنبه تا چهارشنبه
    weekday = today.weekday()  # Mon=0
    # ما می‌خواهیم شنبه را شروع بگیریم → شنبه = -2 نسبت به دوشنبه
    start = today - datetime.timedelta(days=weekday + 2)
    end = start + datetime.timedelta(days=4)
    return start.isoformat(), end.isoformat()


# ---------------------
# DB
# ---------------------

def get_weekly_rows():
    start, end = get_week_range()
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT report_date, market_name, money_flow
        FROM daily_reports
        WHERE report_date BETWEEN ? AND ?
        ORDER BY report_date
        """,
        (start, end),
    )

    rows = cur.fetchall()
    conn.close()
    return rows, start, end


# ---------------------
# Table pivot for image
# ---------------------

def build_week_table():
    rows, start, end = get_weekly_rows()

    week_days = ["Sat", "Sun", "Mon", "Tue", "Wed"]

    table = {}

    for date, market, flow in rows:
        dt = datetime.date.fromisoformat(date)
        day_name = dt.strftime("%a")

        flow = float(flow)

        if market not in table:
            table[market] = {d: "-" for d in week_days}
            table[market]["total"] = 0

        table[market][day_name] = f"{flow:.1f} B"
        table[market]["total"] += flow

    final_rows = []

    for market, vals in table.items():
        final_rows.append(
            [market] + [vals[d] for d in week_days] + [f"{vals['total']:.1f} B"]
        )

    return final_rows, start, end




# ---------------------
# IMAGE
# ---------------------

def generate_weekly_report_image(weekly_rows, start_date, end_date):
    from PIL import Image, ImageDraw, ImageFont

    padding = 20
    row_height = 60

    headers = [
        "بازار",
        "شنبه",
        "یکشنبه",
        "دوشنبه",
        "سه‌شنبه",
        "چهارشنبه",
        "جمع هفته"
    ]

    width = 1300
    height = padding*2 + row_height * (len(weekly_rows)+2)

    img = Image.new("RGB", (width, height), (240, 248, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/mnt/data/IRANSansX-Regular.ttf", 26)
        small = ImageFont.truetype("/mnt/data/IRANSansX-Regular.ttf", 22)
    except:
        font = small = ImageFont.load_default()

    # هدر خاکستری
    draw.rectangle([(padding, padding),
                    (width-padding, padding+row_height)],
                   fill=(210, 210, 210))

    col_w = (width - padding*2) // len(headers)

    for i, h in enumerate(headers):
        draw.text(
            (padding + i*col_w + 10, padding+10),
            h, font=font, fill=(30, 30, 30)
        )

    # ردیف‌ها
    y = padding + row_height

    for market, sat, sun, mon, tue, wed, total in weekly_rows:

        y += 2
        draw.rectangle([(padding, y),
                        (width-padding, y+row_height)],
                       fill=(255, 255, 255))

        cols = [market, sat, sun, mon, tue, wed, total]

        for i, val in enumerate(cols):

            # رنگ مثبت/منفی
            if i > 0 and val not in ("-", ""):
                v = float(str(val).replace("B", "").replace(",", ""))
                if v > 0:
                    bg = (210, 255, 210)
                else:
                    bg = (255, 210, 210)
                draw.rectangle(
                    [(padding + i*col_w,
                      y),
                     (padding + (i+1)*col_w,
                      y+row_height)],
                    fill=bg
                )

            draw.text(
                (padding + i*col_w + 10, y+12),
                str(val), font=font, fill=(0, 0, 0)
            )

        y += row_height

    # 🔹 مرز سیاه کلفت
    border_width = 25
    draw.rectangle(
        [(0, 0), (width-1, height-1)],
        outline=(0, 0, 0),
        width=border_width
    )

    # 🔹 متن پایین تصویر + تاریخ شمسی
    text = f"گزارش هفتگی — از {start_date} تا {end_date}"
    draw.text(
        (padding, height-50),
        text,
        fill=(255, 255, 255),
        font=small
    )

    out = "weekly_report.png"
    img.save(out)
    return out

weekly_rows, start_date, end_date = build_week_table()

path = generate_weekly_report_image(weekly_rows, start_date, end_date)
