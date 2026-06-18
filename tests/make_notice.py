# -*- coding: utf-8 -*-
"""테스트용 생성형 고지서 이미지 생성 (건강보험료 / 전기요금).
실제 고지서처럼 보낸기관·납부번호·항목별 금액·합계·납부기한·안내문구 포함.
실행: <venv>\Scripts\python.exe tests/make_notice.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = r"C:\Windows\Fonts"

def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

R  = lambda s: font("malgun.ttf", s)    # regular
B  = lambda s: font("malgunbd.ttf", s)  # bold

INK = (20, 25, 35)
GRAY = (110, 120, 135)
LINE = (180, 188, 200)
RED = (200, 40, 40)
BLUE = (20, 70, 160)

def new_canvas(w=1000, h=1400):
    img = Image.new("RGB", (w, h), "white")
    return img, ImageDraw.Draw(img)

def hline(d, x1, y, x2, color=LINE, width=2):
    d.line([(x1, y), (x2, y)], fill=color, width=width)

def box(d, x1, y1, x2, y2, color=LINE, width=2):
    d.rectangle([x1, y1, x2, y2], outline=color, width=width)

def right_text(d, x_right, y, text, fnt, fill=INK):
    w = d.textlength(text, font=fnt)
    d.text((x_right - w, y), text, font=fnt, fill=fill)


def make_health():
    img, d = new_canvas()
    M = 60
    W = 1000
    # 상단 기관
    d.text((M, 40), "국민건강보험공단", font=B(40), fill=BLUE)
    d.text((M, 92), "National Health Insurance Service", font=R(20), fill=GRAY)
    hline(d, M, 140, W - M, color=BLUE, width=4)

    # 제목
    d.text((M, 165), "2026년 6월분 건강보험료 납부고지서", font=B(36), fill=INK)
    d.text((M, 218), "(지역가입자)", font=R(24), fill=GRAY)

    # 수신/납부번호
    y = 280
    d.text((M, y), "성    명 :  홍 길 동  귀하", font=R(26), fill=INK)
    d.text((M, y + 44), "납부번호 :  31234-56789-012", font=R(26), fill=INK)
    d.text((M, y + 88), "고지일자 :  2026. 06. 10.", font=R(26), fill=INK)

    # 고지내역 표
    ty = 440
    d.text((M, ty - 44), "■ 고지내역", font=B(26), fill=INK)
    rows = [
        ("건강보험료", "47,210 원"),
        ("장기요양보험료", "6,110 원"),
        ("정산·가산금", "5,100 원"),
    ]
    rh = 64
    box(d, M, ty, W - M, ty + rh * (len(rows) + 1))
    # 헤더행
    d.text((M + 30, ty + 18), "항    목", font=B(24), fill=INK)
    right_text(d, W - M - 30, ty + 18, "금    액", B(24))
    hline(d, M, ty + rh, W - M)
    for i, (k, v) in enumerate(rows):
        ry = ty + rh * (i + 1)
        d.text((M + 30, ry + 18), k, font=R(24), fill=INK)
        right_text(d, W - M - 30, ry + 18, v, R(24))
        if i < len(rows) - 1:
            hline(d, M, ry + rh, W - M, color=(225, 230, 238))
    # 세로 구분선
    d.line([(W // 2 + 120, ty), (W // 2 + 120, ty + rh * (len(rows) + 1))], fill=LINE, width=2)

    # 합계 강조
    sy = ty + rh * (len(rows) + 1) + 30
    box(d, M, sy, W - M, sy + 80, color=BLUE, width=3)
    d.text((M + 30, sy + 22), "납부할 총액", font=B(30), fill=BLUE)
    right_text(d, W - M - 30, sy + 18, "58,420 원", B(38), fill=RED)

    # 납부기한
    dy = sy + 130
    d.text((M, dy), "납부기한", font=B(30), fill=INK)
    d.text((M + 200, dy - 4), "2026년 6월 25일 까지", font=B(34), fill=RED)

    # 안내문
    ay = dy + 90
    hline(d, M, ay, W - M, color=(220, 225, 233))
    notes = [
        "• 납부기한이 지나면 연체금이 부과됩니다.",
        "• 자동이체를 신청하시면 매월 자동으로 납부됩니다.",
        "• 소득·재산이 적은 분은 보험료 경감 신청이 가능합니다.",
        "• 문의 : 국민건강보험공단 ☎ 1577-1000",
    ]
    for i, t in enumerate(notes):
        d.text((M, ay + 30 + i * 46), t, font=R(24), fill=INK)

    # 하단 지로 느낌
    by = ay + 30 + len(notes) * 46 + 40
    box(d, M, by, W - M, by + 110, color=INK, width=2)
    d.text((M + 24, by + 20), "전자납부번호", font=R(20), fill=GRAY)
    d.text((M + 24, by + 48), "3 1234 5678 9012 3", font=B(34), fill=INK)
    right_text(d, W - M - 24, by + 20, "수납기관", R(20), fill=GRAY)
    right_text(d, W - M - 24, by + 48, "국민건강보험공단", B(26))

    path = os.path.join(OUT_DIR, "notice_health.png")
    img.save(path)
    return path


def make_electricity():
    img, d = new_canvas()
    M = 60
    W = 1000
    d.text((M, 40), "한국전력공사", font=B(40), fill=(30, 90, 60))
    d.text((M, 92), "KEPCO 전기요금 청구서", font=R(22), fill=GRAY)
    hline(d, M, 140, W - M, color=(30, 120, 80), width=4)

    d.text((M, 165), "2026년 6월 전기요금 청구서", font=B(36), fill=INK)

    y = 250
    d.text((M, y), "고객명 :  김 영 자  님", font=R(26), fill=INK)
    d.text((M, y + 44), "고객번호 :  0123-4567-890", font=R(26), fill=INK)
    d.text((M, y + 88), "사용기간 :  2026.05.11 ~ 2026.06.10", font=R(26), fill=INK)
    d.text((M, y + 132), "사용량 :  185 kWh", font=R(26), fill=INK)

    ty = 460
    d.text((M, ty - 44), "■ 요금내역", font=B(26), fill=INK)
    rows = [
        ("기본요금", "1,600 원"),
        ("전력량요금", "22,840 원"),
        ("기후환경요금", "1,665 원"),
        ("부가가치세", "2,610 원"),
        ("전력산업기반기금", "940 원"),
    ]
    rh = 56
    box(d, M, ty, W - M, ty + rh * (len(rows) + 1))
    d.text((M + 30, ty + 14), "항    목", font=B(24), fill=INK)
    right_text(d, W - M - 30, ty + 14, "금    액", B(24))
    hline(d, M, ty + rh, W - M)
    for i, (k, v) in enumerate(rows):
        ry = ty + rh * (i + 1)
        d.text((M + 30, ry + 14), k, font=R(24), fill=INK)
        right_text(d, W - M - 30, ry + 14, v, R(24))
        if i < len(rows) - 1:
            hline(d, M, ry + rh, W - M, color=(225, 230, 238))
    d.line([(W // 2 + 120, ty), (W // 2 + 120, ty + rh * (len(rows) + 1))], fill=LINE, width=2)

    sy = ty + rh * (len(rows) + 1) + 30
    box(d, M, sy, W - M, sy + 80, color=(30, 120, 80), width=3)
    d.text((M + 30, sy + 22), "청구금액", font=B(30), fill=(30, 120, 80))
    right_text(d, W - M - 30, sy + 18, "29,655 원", B(38), fill=RED)

    dy = sy + 130
    d.text((M, dy), "납기일", font=B(30), fill=INK)
    d.text((M + 160, dy - 4), "2026년 6월 28일 까지", font=B(34), fill=RED)

    ay = dy + 90
    hline(d, M, ay, W - M, color=(220, 225, 233))
    notes = [
        "• 납기일이 지나면 연체료가 부과됩니다.",
        "• 요금 부담이 어려우시면 복지할인 제도를 확인하세요.",
        "• 기초생활수급자·차상위계층은 전기요금 할인 대상입니다.",
        "• 문의 : 한국전력공사 ☎ 123",
    ]
    for i, t in enumerate(notes):
        d.text((M, ay + 30 + i * 46), t, font=R(24), fill=INK)

    path = os.path.join(OUT_DIR, "notice_electricity.png")
    img.save(path)
    return path


if __name__ == "__main__":
    p1 = make_health()
    p2 = make_electricity()
    print("생성 완료:")
    print(" -", p1)
    print(" -", p2)
