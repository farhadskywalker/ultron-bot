import sqlite3
import datetime
import jdatetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
import arabic_reshaper
from bidi.algorithm import get_display

DB_PATH = "market_data.db"
FONT_REG = "IRANSansX-Regular.ttf"
FONT_BOLD = "IRANSansX-Bold.ttf"

# ----------------------------- Helpers -----------------------------

def to_jalali(date_iso: str) -> str:
    y, m, d = map(int, date_iso.split("-"))
    j = jdatetime.date.fromgregorian(year=y, month=m, day=d)
    return j.strftime("%Y/%m/%d")

def get_week_range():
    today = datetime.date.today()

    # تبدیل تقویم: شنبه = 0
    dow = (today.weekday() + 2) % 7

    start = today - datetime.timedelta(days=dow)
    end = start + datetime.timedelta(days=4)

    return start.isoformat(), end.isoformat()


# ----------------------------- DB -----------------------------

def get_weekly_rows():
    start, end = get_week_range()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT report_date, market_name, money_flow
        FROM daily_reports
        WHERE report_date BETWEEN ? AND ?
        ORDER BY report_date ASC
    """, (start, end))
    rows = cur.fetchall()
    conn.close()
    print("START:", start)
    print("END:", end)
    print("ROWS:", rows)
    return rows, start, end


# ----------------------------- Build Pivot -----------------------------

def build_week_table():
    rows, start, end = get_weekly_rows()

    # روزهای هفته
    week_days = ["Sat","Sun","Mon","Tue","Wed"]

    table = {}
    for date_iso, market, flow in rows:
        d = datetime.date.fromisoformat(date_iso)
        day_name = d.strftime("%a")  # Sat, Sun...
        if market not in table:
            table[market] = {d: "-" for d in week_days}
            table[market]["total"] = 0.0
        # مقدار پول *B -> عدد
        try:
            v = float(str(flow).replace(" B","").replace(",",""))
        except:
            v = 0.0
        table[market][day_name] = f"{v:.1f} B"
        table[market]["total"] += v

    final_rows = []
    for m, vals in table.items():
        final_rows.append(
            [m] + [vals[d] for d in week_days] + [f"{vals['total']:.1f} B"]
        )

    return final_rows, start, end

# ----------------------------- Image -----------------------------

def generate_weekly_report_image(weekly_rows, start_date, end_date):
    # طراحی مثل گزارش لحظه‌ای
    headers = [
        "بازار",
        "شنبه",
        "یکشنبه",
        "دوشنبه",
        "سه‌شنبه",
        "چهارشنبه",
        "جمع هفته"
    ]

    # اندازه‌ها
    padding = 30
    row_h = 90
    col_widths = [260, 170,170,170,170,170,220]
    width = sum(col_widths) + padding*2
    height = padding*2 + row_h*(len(weekly_rows)+1) + 80

    base = Image.new("RGB",(width,height),"white")
    draw = ImageDraw.Draw(base)

    font = ImageFont.truetype(FONT_REG,26)
    font_b = ImageFont.truetype(FONT_BOLD,32)

    # رسم هدر
    y = padding
    draw.rectangle([(padding,y),(width-padding,y+row_h)],fill=(230,230,230))
    x = padding
    for i,h in enumerate(headers[::-1]):  # راست به چپ
        txt = get_display(arabic_reshaper.reshape(h))
        draw.text((x+10,y+25), txt, fill=(20,20,20), font=font_b)
        x += col_widths[::-1][i]

    # رسم ردیف‌ها
    y += row_h
    for row in weekly_rows:
        x = padding
        rev = row[::-1]
        for j,cell in enumerate(rev):
            # رنگ
            bg = (235,245,255)  # آبی خیلی کمرنگ
            if j == 0:  # بازار
                bg = (225,235,255)
            elif j == len(rev)-1:  # جمع هفته
                # مثبت یا منفی
                try:
                    fv = float(cell.replace(" B","").replace(",",""))
                    bg = (230,255,230) if fv>=0 else (255,230,230)
                except:
                    bg = (245,245,245)
            # رسم
            cw = col_widths[::-1][j]
            draw.rectangle([(x,y),(x+cw,y+row_h)],fill=bg)
            txt = get_display(arabic_reshaper.reshape(cell))
            draw.text((x+10,y+25), txt, fill=(30,30,30), font=font)
            x += cw
        y += row_h

    # متن پایین
    js = to_jalali(start_date)
    je = to_jalali(end_date)
    foot = f"بازه گزارش هفتگی: {js} تا {je}"
    txtf = get_display(arabic_reshaper.reshape(foot))
    draw.text((padding, height-60), txtf, fill=(0,0,0), font=font_b)

    # حاشیه سیاه
    bordered = ImageOps.expand(base,border=25,fill="black")

    path = "weekly_report.png"
    bordered.save(path)
    return path

# ----------------------------- Test Run -----------------------------

if __name__ == "__main__":
    rows, s,e = build_week_table()
    generate_weekly_report_image(rows,s,e)
