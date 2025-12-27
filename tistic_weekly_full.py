# tistic – weekly image + db (with Jalali dates using jdatetime)

import sqlite3
import datetime
import jdatetime
from PIL import Image, ImageDraw, ImageFont,ImageOps

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

    # ستون‌ها — به ترتیب هفته
    week_days = ["Sat", "Sun", "Mon", "Tue", "Wed"]

    table = {}

    for date, market, flow in rows:
        dt = datetime.date.fromisoformat(date)
        day_name = dt.strftime("%a")

        if market not in table:
            table[market] = {d: "-" for d in week_days}
            table[market]["total"] = 0.0

        # ذخیره مقدار هر روز
        table[market][day_name] = f"{float(flow):.1f} B"

        # جمع هفتگی
        table[market]["total"] += float(flow)

    # ساخت آرایه نهایی (راست به چپ)
    final_rows = []

    for market, vals in table.items():
        final_rows.append(
            [
                market,
                vals["Sat"],
                vals["Sun"],
                vals["Mon"],
                vals["Tue"],
                vals["Wed"],
                f"{vals['total']:.1f} B"
            ]
        )

    return final_rows, start, end





# ---------------------
# IMAGE
# ---------------------

def generate_weekly_report_image(weekly_rows, start_date, end_date):
    from bidi.algorithm import get_display
    import arabic_reshaper
    from khayyam import JalaliDatetime

    width = 1400
    row_height = 95
    padding = 40
    header_bg = (230, 230, 230)
    positive_bg = (230, 255, 230)
    negative_bg = (255, 230, 230)
    neutral_bg  = (230, 240, 255)
    text_color = (30, 30, 30)

    font = ImageFont.truetype("IRANSansX-Regular.ttf", 34)
    font_bold = ImageFont.truetype("IRANSansX-Bold.ttf", 38)

    headers = [
        "بازار",
        "شنبه",
        "یکشنبه",
        "دوشنبه",
        "سه‌شنبه", 
        "چهارشنبه",
        "جمع هفته"
    ]

    col_widths = [280, 160, 160, 160, 160, 160, 200]

    height = padding*2 + row_height * (len(weekly_rows)+1)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # هدر
    y = padding
    x = padding

    for i, h in enumerate(headers):
        txt = get_display(arabic_reshaper.reshape(h))
        draw.rectangle([(x, y), (x+col_widths[i], y+row_height)], fill=header_bg)
        draw.text((x+10, y+25), txt, fill=text_color, font=font_bold)
        x += col_widths[i]

    y += row_height

    # ردیف‌ها
    for row in weekly_rows:
        x = padding

        for i, cell in enumerate(row):

            bg = neutral_bg

            if i >= 1:     # ستون‌های عددی
                if str(cell).startswith("-"):
                    bg = negative_bg
                elif cell != "-":
                    bg = positive_bg

            draw.rectangle([(x, y), (x+col_widths[i], y+row_height)], fill=bg)

            txt = get_display(arabic_reshaper.reshape(str(cell)))
            draw.text((x+10, y+25), txt, fill=text_color, font=font)

            x += col_widths[i]

        y += row_height

    # قاب سیاه دور عکس
    border_width = 22
    bordered = ImageOps.expand(img, border=border_width, fill="black")
    draw2 = ImageDraw.Draw(bordered)

    # متن پایین — تاریخ شمسی
    start_j = JalaliDatetime.strptime(start_date, "%Y-%m-%d").strftime("%Y/%m/%d")
    end_j   = JalaliDatetime.strptime(end_date, "%Y-%m-%d").strftime("%Y/%m/%d")

    caption = f"گزارش هفتگی بازار — بازه: {start_j} تا {end_j}"

    caption = get_display(arabic_reshaper.reshape(caption))

    draw2.text(
        (padding, bordered.height - 55),
        caption,
        fill=(255, 255, 255),
        font=font
    )

    bordered.save("weekly_report.png")
    return "weekly_report.png"



weekly_rows, start_date, end_date = build_week_table()
path = generate_weekly_report_image(weekly_rows, start_date, end_date)
print("DONE:", path)
