#!/usr/bin/env python3
from __future__ import annotations
import json, math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

OUT=Path("benchmarks/ocr_a32/fixtures")
GT=OUT/"ground_truth.json"

FIXTURES={
 "clear":{
   "text":"هذا مستند قانوني اصطناعي لاختبار القراءة العربية\nرقم الصك 351992847\nالحكم محل المراجعة فقط وليس حقيقة قانونية",
   "rotate":0,"noise":0,"blur":0
 },
 "numeric":{
   "text":"إيصال قانوني اصطناعي رقم 48219\nالتاريخ 2024-05-17\nالمبلغ الإجمالي 12500.75 ريال\nرقم القضية 4870236421",
   "rotate":0,"noise":0,"blur":0
 },
 "arabic_indic":{
   "text":"رقم الصك ٣٥١٩٩٢٨٤٧\nالتاريخ ١٤٤٨-٠٤-١٨\nالمبلغ ١٢٥٠٠ ريال\nرقم القضية ٤٨٧٠٢٣٦٤٢١",
   "rotate":0,"noise":0,"blur":0
 },
 "rotated":{
   "text":"محضر جلسة اصطناعي للاختبار فقط\nتم تأييد الحكم الابتدائي في المثال الاصطناعي\nرقم المرجع 778899",
   "rotate":2.0,"noise":0,"blur":0
 },
 "low_quality":{
   "text":"صورة منخفضة الجودة لاختبار المراجعة البشرية\nالمبلغ 75000 ريال\nالتاريخ 2025-01-10\nرقم المستند 99887766",
   "rotate":0,"noise":22,"blur":1.2
 },
}

def font_path():
    candidates=[
      r"C:\Windows\Fonts\tahoma.ttf",
      r"C:\Windows\Fonts\arial.ttf",
      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists(): return p
    raise FileNotFoundError("Arabic-capable font not found")

def rtl_line(s:str)->str:
    return get_display(arabic_reshaper.reshape(s))

def render(name,cfg,font):
    img=Image.new("RGB",(1500,950),"white")
    draw=ImageDraw.Draw(img)
    y=90
    for line in cfg["text"].splitlines():
        shown=rtl_line(line)
        bbox=draw.textbbox((0,0),shown,font=font)
        w=bbox[2]-bbox[0]
        draw.text((1420-w,y),shown,font=font,fill="black")
        y+=135
    if cfg["blur"]:
        img=img.filter(ImageFilter.GaussianBlur(cfg["blur"]))
    if cfg["noise"]:
        px=img.load(); rnd=random.Random(100+len(name))
        for _ in range(cfg["noise"]*1100):
            x=rnd.randrange(img.width); y=rnd.randrange(img.height)
            v=rnd.randrange(80,220)
            px[x,y]=(v,v,v)
    if cfg["rotate"]:
        img=img.rotate(cfg["rotate"],expand=False,fillcolor="white")
    path=OUT/f"{name}.png"; img.save(path,quality=95)
    return path

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype(font_path(),64)
    manifest={}
    for name,cfg in FIXTURES.items():
        path=render(name,cfg,font)
        manifest[name]={"path":str(path),"expected_text":cfg["text"]}
    # Deliberately invalid fixture for recovery/isolation behavior.
    bad=OUT/"corrupt.png"; bad.write_bytes(b"not-a-valid-image")
    manifest["corrupt"]={"path":str(bad),"expected_text":"","expected_failure":True}
    GT.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(GT)

if __name__=="__main__": main()
