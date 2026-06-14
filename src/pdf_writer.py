import os
from datetime import datetime

import fitz  # PyMuPDF


FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
FONT_NAME = "malgun"


def clean_text(text):
    text = str(text)
    text = text.replace("�", "-")
    text = text.replace("\t", " ")
    text = " ".join(text.split())
    return text.strip()


def split_long_line(text, max_len=44):
    # 한 줄이 너무 길면 PDF 폭에 맞게 자름
    lines = []
    text = clean_text(text)

    while len(text) > max_len:
        lines.append(text[:max_len])
        text = text[max_len:]

    if text:
        lines.append(text)

    return lines


def add_text(page, text, x, y, font_size=11):
    # malgun.ttf를 직접 지정해서 한글 자간 깨짐을 줄임
    if os.path.exists(FONT_PATH):
        page.insert_text(
            (x, y),
            text,
            fontsize=font_size,
            fontname=FONT_NAME,
            fontfile=FONT_PATH
        )
    else:
        page.insert_text(
            (x, y),
            text,
            fontsize=font_size,
            fontname="korea"
        )


def add_wrapped_text(page, text, x, y, max_len=44, font_size=10.5, line_gap=18):
    lines = split_long_line(text, max_len=max_len)

    for line in lines:
        add_text(page, line, x, y, font_size=font_size)
        y += line_gap

    return y


def save_emergency_guide_pdf(guide_text, filename=None):
    os.makedirs("output", exist_ok=True)

    if filename is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"응급처치_가이드_{now}.pdf"

    file_path = os.path.join("output", filename)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    margin_x = 50
    start_y = 70
    y = start_y
    line_gap = 18
    page_bottom = 790

    lines = guide_text.split("\n")

    if not lines:
        lines = ["응급처치 가이드"]

    title = clean_text(lines[0])

    # 제목
    add_text(page, title, margin_x, y, font_size=22)
    y += 34

    # 부제
    add_text(page, "RAG 기반 응급처치 참고 가이드", margin_x, y, font_size=11)
    y += 28

    # 구분선
    page.draw_line(
        (margin_x, y),
        (545, y),
        color=(0, 0, 0),
        width=0.6
    )
    y += 24

    for raw_line in lines[1:]:
        line = clean_text(raw_line)

        if not line:
            y += 8
            continue

        # 새 페이지 처리
        if y > page_bottom:
            page = doc.new_page(width=595, height=842)
            y = start_y

        # 섹션 제목
        if line.startswith("[") and "]" in line:
            y += 10

            if y > page_bottom:
                page = doc.new_page(width=595, height=842)
                y = start_y

            add_text(page, line, margin_x, y, font_size=15)
            y += 26
            continue

        # 주의 문구
        if line.startswith("※"):
            y = add_wrapped_text(
                page,
                line,
                margin_x,
                y,
                max_len=48,
                font_size=10,
                line_gap=line_gap
            )
            continue

        # 일반 문장 또는 항목
        y = add_wrapped_text(
            page,
            line,
            margin_x,
            y,
            max_len=50,
            font_size=10.5,
            line_gap=line_gap
        )

    doc.save(file_path, garbage=4, deflate=True)
    doc.close()

    print(f"응급처치 가이드 PDF 저장 완료: {file_path}")

    return file_path