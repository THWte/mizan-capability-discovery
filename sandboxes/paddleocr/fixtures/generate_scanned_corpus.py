"""
Generates a SYNTHETIC scanned (raster, no text layer) Arabic corpus for OCR
benchmarking. No real case file, personal data, or legal document is used.

Engine-neutral by design: reused/extended from the equivalent generator in
`sandboxes/docling/fixtures/generate_scanned_corpus.py` (same methodology,
same ground-truth style) per the A4 PaddleOCR Capability Gate instruction to
reuse engine-neutral benchmark methodology, fixtures, and metric
definitions across engines rather than reinventing them. This copy adds the
Arabic-Indic digits, rotated, blank-page, noisy-page, and multi-block cases
required by A4 STEP 12 that were not present in the Docling generator.

Each "document" is produced by rendering text onto a raster image with PIL
(simulating a scanned page) and then embedding that image into a PDF as an
image XObject only — i.e. the resulting PDF has NO extractable text layer,
which is what makes this a valid test of Docling's actual OCR path rather
than its (much easier) text-layer extraction path.

Ground truth for each document is saved alongside it as a `.txt` file with
the same stem, plus a consolidated `manifest.json`, so CER/WER can be
computed and re-verified independently of this script.
"""
from __future__ import annotations

import json
import pathlib
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import arabic_reshaper
from bidi.algorithm import get_display

_WESTERN_TO_ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

OUT_DIR = pathlib.Path(__file__).parent
PAGE_W, PAGE_H = 1600, 2263  # ~A4 at 200dpi

FONT_CANDIDATES = [
    pathlib.Path(r"C:\Windows\Fonts\arial.ttf"),
    pathlib.Path(r"C:\Windows\Fonts\tahoma.ttf"),
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for f in FONT_CANDIDATES:
        if f.exists():
            return ImageFont.truetype(str(f), size)
    raise RuntimeError("No usable TrueType font found for rendering Arabic text")


def shaped(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def render_lines_to_image(lines: list[str], font_size: int = 48) -> Image.Image:
    img = Image.new("L", (PAGE_W, PAGE_H), color=255)
    draw = ImageDraw.Draw(img)
    font = _font(font_size)
    y = 120
    for line in lines:
        display_line = shaped(line) if any("\u0600" <= ch <= "\u06ff" for ch in line) else line
        bbox = draw.textbbox((0, 0), display_line, font=font)
        text_w = bbox[2] - bbox[0]
        x = PAGE_W - 120 - text_w  # right-align for Arabic-style documents
        draw.text((x, y), display_line, font=font, fill=0)
        y += font_size + 40
    return img


def render_table_to_image() -> Image.Image:
    img = Image.new("L", (PAGE_W, PAGE_H), color=255)
    draw = ImageDraw.Draw(img)
    font = _font(40)
    title = shaped("جدول تجريبي اصطناعي للفواتير")
    draw.text((PAGE_W - 120 - draw.textbbox((0, 0), title, font=font)[2], 100), title, font=font, fill=0)

    headers = ["الحالة", "المبلغ", "التاريخ", "رقم الفاتورة"]
    rows = [
        ["مقبولة", "1500", "2024-01-10", "INV-001"],
        ["معلقة", "750", "2024-02-20", "INV-002"],
        ["مرفوضة", "3200", "2024-03-05", "INV-003"],
    ]
    col_w = (PAGE_W - 240) // 4
    top = 260
    row_h = 90
    # Header row
    for i, h in enumerate(headers):
        text = shaped(h)
        cell_x0 = 120 + i * col_w
        draw.rectangle([cell_x0, top, cell_x0 + col_w, top + row_h], outline=0, width=2)
        tw = draw.textbbox((0, 0), text, font=font)[2]
        draw.text((cell_x0 + (col_w - tw) // 2, top + 20), text, font=font, fill=0)
    # Data rows
    for r, row in enumerate(rows):
        row_top = top + row_h * (r + 1)
        for i, cell in enumerate(row):
            text = shaped(cell) if any("\u0600" <= ch <= "\u06ff" for ch in cell) else cell
            cell_x0 = 120 + i * col_w
            draw.rectangle([cell_x0, row_top, cell_x0 + col_w, row_top + row_h], outline=0, width=2)
            tw = draw.textbbox((0, 0), text, font=font)[2]
            draw.text((cell_x0 + (col_w - tw) // 2, row_top + 20), text, font=font, fill=0)
    return img


def save_as_scanned_pdf(img: Image.Image, pdf_path: pathlib.Path) -> None:
    png_path = pdf_path.with_suffix(".png")
    img.save(png_path)
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    # Draw the raster image to fill the page; no text operators are emitted,
    # so the resulting PDF has no extractable text layer.
    c.drawImage(str(png_path), 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    c.save()
    png_path.unlink()  # keep only the PDF in version control


def main() -> None:
    manifest = {}

    # 1. Clear Arabic paragraph
    lines_clear = [
        "هذا مستند ممسوح ضوئيًا اصطناعي وليس ملف قضية حقيقي",
        "العنوان: محضر اجتماع تجريبي خيالي",
        "تم إعداد هذا النص فقط لاختبار جودة التعرف الضوئي على الحروف",
        "يجب أن يقرأ النظام هذا النص بدقة معقولة دون وجود طبقة نص أصلية",
    ]
    img = render_lines_to_image(lines_clear)
    pdf_path = OUT_DIR / "scanned_arabic_clear.pdf"
    save_as_scanned_pdf(img, pdf_path)
    expected_clear = "\n".join(lines_clear)
    (OUT_DIR / "scanned_arabic_clear.expected.txt").write_text(expected_clear, encoding="utf-8")
    manifest["scanned_arabic_clear.pdf"] = {
        "description": "Clear synthetic scanned Arabic paragraph",
        "expected_file": "scanned_arabic_clear.expected.txt",
    }

    # 2. Arabic + numbers + date + amount
    lines_numeric = [
        "إيصال تجريبي اصطناعي رقم 48219",
        "التاريخ: 2024-05-17",
        "المبلغ الإجمالي: 12500.75 ريال (رقم وهمي)",
        "اسم العميل الوهمي: محمد الاختباري",
    ]
    img = render_lines_to_image(lines_numeric)
    pdf_path = OUT_DIR / "scanned_arabic_numeric.pdf"
    save_as_scanned_pdf(img, pdf_path)
    expected = "\n".join(lines_numeric)
    (OUT_DIR / "scanned_arabic_numeric.expected.txt").write_text(expected, encoding="utf-8")
    manifest["scanned_arabic_numeric.pdf"] = {
        "description": "Synthetic scanned Arabic with numbers, date, and amount",
        "expected_file": "scanned_arabic_numeric.expected.txt",
    }

    # 3. Mixed Arabic/English
    lines_mixed = [
        "SYNTHETIC SCANNED MIXED DOCUMENT - NOT REAL",
        "القسم الأول: نص عربي تجريبي ضمن مستند ممسوح ضوئيًا",
        "Section Two: English fictional clause for OCR testing only.",
        "القسم الثالث: نهاية المستند التجريبي",
    ]
    img = render_lines_to_image(lines_mixed)
    pdf_path = OUT_DIR / "scanned_mixed_ar_en.pdf"
    save_as_scanned_pdf(img, pdf_path)
    expected = "\n".join(lines_mixed)
    (OUT_DIR / "scanned_mixed_ar_en.expected.txt").write_text(expected, encoding="utf-8")
    manifest["scanned_mixed_ar_en.pdf"] = {
        "description": "Synthetic scanned mixed Arabic/English document",
        "expected_file": "scanned_mixed_ar_en.expected.txt",
    }

    # 4. Arabic table
    img = render_table_to_image()
    pdf_path = OUT_DIR / "scanned_arabic_table.pdf"
    save_as_scanned_pdf(img, pdf_path)
    expected_table = (
        "جدول تجريبي اصطناعي للفواتير\n"
        "رقم الفاتورة التاريخ المبلغ الحالة\n"
        "INV-001 2024-01-10 1500 مقبولة\n"
        "INV-002 2024-02-20 750 معلقة\n"
        "INV-003 2024-03-05 3200 مرفوضة"
    )
    (OUT_DIR / "scanned_arabic_table.expected.txt").write_text(expected_table, encoding="utf-8")
    manifest["scanned_arabic_table.pdf"] = {
        "description": "Synthetic scanned simple Arabic invoice table (rendered as a raster grid, not a real table object)",
        "expected_file": "scanned_arabic_table.expected.txt",
    }

    # 5. Low-quality scan (downscale + blur + noise) of the clear document
    img_clear = render_lines_to_image(lines_clear)
    small = img_clear.resize((PAGE_W // 3, PAGE_H // 3), Image.BILINEAR)
    low_quality = small.resize((PAGE_W, PAGE_H), Image.BILINEAR)
    low_quality = low_quality.filter(ImageFilter.GaussianBlur(radius=2.2))
    pdf_path = OUT_DIR / "scanned_arabic_low_quality.pdf"
    save_as_scanned_pdf(low_quality, pdf_path)
    (OUT_DIR / "scanned_arabic_low_quality.expected.txt").write_text(expected_clear, encoding="utf-8")
    manifest["scanned_arabic_low_quality.pdf"] = {
        "description": "Same clear-text content, downscaled 3x and Gaussian-blurred to simulate a low-quality scan",
        "expected_file": "scanned_arabic_low_quality.expected.txt",
        "note": "expected_file intentionally reused from scanned_arabic_clear content, NOT the numeric one",
    }

    # 6. Arabic-Indic digits (distinct glyphs from Western 0-9; PaddleOCR
    # adversarial case per A4 STEP 12 — a separate case from "numeric" above,
    # which uses Western digits).
    lines_indic = [
        "إيصال تجريبي اصطناعي رقم ٤٨٢١٩",
        "التاريخ: ٢٠٢٤-٠٥-١٧",
        "المبلغ الإجمالي: ١٢٥٠٠.٧٥ ريال (رقم وهمي)",
    ]
    img = render_lines_to_image(lines_indic)
    pdf_path = OUT_DIR / "scanned_arabic_indic_digits.pdf"
    save_as_scanned_pdf(img, pdf_path)
    expected_indic = "\n".join(lines_indic)
    (OUT_DIR / "scanned_arabic_indic_digits.expected.txt").write_text(expected_indic, encoding="utf-8")
    manifest["scanned_arabic_indic_digits.pdf"] = {
        "description": "Synthetic scanned Arabic using Arabic-Indic digit glyphs (٠-٩), not Western 0-9",
        "expected_file": "scanned_arabic_indic_digits.expected.txt",
    }

    # 7. Rotated scan (simulates a page fed crooked into a scanner)
    img_clear2 = render_lines_to_image(lines_clear)
    rotated = img_clear2.rotate(7, expand=True, fillcolor=255)
    pdf_path = OUT_DIR / "scanned_arabic_rotated.pdf"
    save_as_scanned_pdf(rotated, pdf_path)
    (OUT_DIR / "scanned_arabic_rotated.expected.txt").write_text(expected_clear, encoding="utf-8")
    manifest["scanned_arabic_rotated.pdf"] = {
        "description": "Same clear-text content rotated 7 degrees to simulate a crooked scan",
        "expected_file": "scanned_arabic_rotated.expected.txt",
        "note": "expected_file intentionally reused from scanned_arabic_clear content",
    }

    # 8. Blank page (no text at all — must not hallucinate content)
    blank = Image.new("L", (PAGE_W, PAGE_H), color=255)
    pdf_path = OUT_DIR / "scanned_blank_page.pdf"
    save_as_scanned_pdf(blank, pdf_path)
    (OUT_DIR / "scanned_blank_page.expected.txt").write_text("", encoding="utf-8")
    manifest["scanned_blank_page.pdf"] = {
        "description": "Fully blank synthetic page; expected output is empty text",
        "expected_file": "scanned_blank_page.expected.txt",
    }

    # 9. Noisy page (random salt-and-pepper style noise, distinct from the
    # Gaussian-blur low-quality case above)
    rng = random.Random(1234)
    img_clear3 = render_lines_to_image(lines_clear)
    noisy = img_clear3.copy()
    px = noisy.load()
    w, h = noisy.size
    noise_fraction = 0.04
    for _ in range(int(w * h * noise_fraction)):
        x = rng.randrange(w)
        y = rng.randrange(h)
        px[x, y] = rng.choice([0, 255])
    pdf_path = OUT_DIR / "scanned_arabic_noisy.pdf"
    save_as_scanned_pdf(noisy, pdf_path)
    (OUT_DIR / "scanned_arabic_noisy.expected.txt").write_text(expected_clear, encoding="utf-8")
    manifest["scanned_arabic_noisy.pdf"] = {
        "description": "Same clear-text content with ~4% random salt-and-pepper pixel noise",
        "expected_file": "scanned_arabic_noisy.expected.txt",
        "note": "expected_file intentionally reused from scanned_arabic_clear content",
    }

    # 10. Multiple distinct text blocks at different page positions (tests
    # content-ordering / multi-block detection, not just single-paragraph OCR)
    img = Image.new("L", (PAGE_W, PAGE_H), color=255)
    draw = ImageDraw.Draw(img)
    font_block = _font(44)
    block_lines = [
        ("أعلى الصفحة: القسم الأول من مستند تجريبي", 150),
        ("منتصف الصفحة: القسم الثاني منفصل عن الأول", 1000),
        ("أسفل الصفحة: القسم الثالث والأخير من المستند", 1900),
    ]
    for text, y in block_lines:
        display_line = shaped(text)
        bbox = draw.textbbox((0, 0), display_line, font=font_block)
        text_w = bbox[2] - bbox[0]
        x = PAGE_W - 120 - text_w
        draw.text((x, y), display_line, font=font_block, fill=0)
    pdf_path = OUT_DIR / "scanned_arabic_multi_block.pdf"
    save_as_scanned_pdf(img, pdf_path)
    expected_multi = "\n".join(t for t, _ in block_lines)
    (OUT_DIR / "scanned_arabic_multi_block.expected.txt").write_text(expected_multi, encoding="utf-8")
    manifest["scanned_arabic_multi_block.pdf"] = {
        "description": "Three distinct Arabic text blocks at top/middle/bottom of the page, in top-to-bottom reading order",
        "expected_file": "scanned_arabic_multi_block.expected.txt",
    }

    (OUT_DIR / "scanned_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Scanned corpus generated:", list(manifest.keys()))


if __name__ == "__main__":
    main()
