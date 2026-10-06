#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
import fitz

ARABIC = (
    "المحكمة المدعي المدعى عليه الحكم الأسباب الوقائع المستند الدعوى الطلب "
    "الاستئناف المادة العقد المبلغ التاريخ الطرف الواقعة الإثبات القرار "
)

def find_font() -> str:
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\seguiemj.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    raise FileNotFoundError("No Unicode font found for Arabic fixture generation")

def page_text(page_no:int, words:int=900) -> str:
    heading = ["الوقائع","الأسباب","المنطوق","الطلبات"][page_no % 4]
    body = (ARABIC * ((words // len(ARABIC.split())) + 2)).split()
    return heading + "\n" + " ".join(body[:words]) + f"\nPAGE_MARKER_{page_no:04d}"

def build_digital_pdf(path:Path, pages:int=100, words_per_page:int=900) -> None:
    font=find_font()
    doc=fitz.open()
    for i in range(1,pages+1):
        page=doc.new_page(width=595,height=842)
        text=page_text(i,words_per_page)
        rc=fitz.Rect(40,40,555,802)
        page.insert_textbox(rc,text,fontsize=9,fontname="mizanfont",fontfile=font,align=fitz.TEXT_ALIGN_RIGHT)
    doc.save(path,garbage=4,deflate=True)
    doc.close()

def build_mixed_pdf(digital:Path,mixed:Path,scan_every:int=10) -> None:
    src=fitz.open(digital)
    out=fitz.open()
    for idx in range(src.page_count):
        p=src.load_page(idx)
        target=out.new_page(width=p.rect.width,height=p.rect.height)
        if (idx+1) % scan_every == 0:
            pix=p.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False)
            target.insert_image(target.rect,stream=pix.tobytes("png"))
        else:
            target.show_pdf_page(target.rect,src,idx)
    out.save(mixed,garbage=4,deflate=True)
    out.close(); src.close()

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    out=Path("benchmarks/long_documents/fixtures")
    out.mkdir(parents=True,exist_ok=True)
    digital=out/"a31_arabic_100p_digital.pdf"
    mixed=out/"a31_arabic_100p_mixed.pdf"
    build_digital_pdf(digital)
    build_mixed_pdf(digital,mixed)
    print("digital",digital,sha256(digital))
    print("mixed",mixed,sha256(mixed))

if __name__=="__main__":
    main()
