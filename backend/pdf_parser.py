"""PDF解析 - 复用已验证版本"""
import fitz, re, json, os, unicodedata
from backend.config import PARSED_DIR

def clean_text(text: str) -> str:
    for sp in ['\u2000','\u2001','\u2002','\u2003','\u2004','\u2005','\u2006','\u2007','\u2008','\u2009','\u200a','\u200b','\u00a0','\u3000','\u202f','\u205f','\u2060']:
        text = text.replace(sp, ' ')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return unicodedata.normalize('NFKC', text)

def parse_pdf(filepath: str, textbook_id: str) -> dict:
    doc = fitz.open(filepath)
    chapters = []
    current_chapter = None
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        ph = page.rect.height
        parts = []
        for b in blocks:
            x0,y0,x1,y1,text,bt,_ = b
            if bt==1: continue
            if y0<ph*0.08 or y1>ph*0.92: continue
            text = clean_text(text.strip())
            if not text: continue
            if re.match(r'^\s*\d{1,4}\s*$', text) and len(text)<5: continue
            parts.append(text)
        page_text = "\n".join(parts)
        # 章节标题
        ch_title = None
        for line in parts[:5]:
            line = clean_text(line.strip())
            if re.match(r'第[一二三四五六七八九十\d]+章', line):
                ch_title = line
                break
        if ch_title:
            if current_chapter:
                current_chapter["content"]="\n".join(current_chapter["_parts"])
                current_chapter["char_count"]=len(current_chapter["content"])
                del current_chapter["_parts"]
                chapters.append(current_chapter)
            current_chapter={"chapter_id":f"ch_{len(chapters)+1:02d}","title":ch_title,"page_start":page_num+1,"page_end":page_num+1,"_parts":[]}
        if current_chapter:
            current_chapter["_parts"].append(page_text)
            current_chapter["page_end"]=page_num+1

    if current_chapter:
        current_chapter["content"]="\n".join(current_chapter["_parts"])
        current_chapter["char_count"]=len(current_chapter["content"])
        del current_chapter["_parts"]
        chapters.append(current_chapter)

    # 合并同章
    merged=[]
    for ch in chapters:
        m=re.match(r'(第[一二三四五六七八九十\d]+章)',ch["title"])
        cn=m.group(1) if m else ch["title"]
        if merged and re.match(r'(第[一二三四五六七八九十\d]+章)',merged[-1]["title"]):
            pn=re.match(r'(第[一二三四五六七八九十\d]+章)',merged[-1]["title"]).group(1)
            if pn==cn:
                merged[-1]["content"]+="\n"+ch["content"]
                merged[-1]["char_count"]+=ch["char_count"]
                merged[-1]["page_end"]=ch["page_end"]
                continue
        merged.append(ch)

    for i,ch in enumerate(merged):
        ch["chapter_id"]=f"ch_{i+1:02d}"

    total_pages = len(doc)
    doc.close()

    if not merged:
        merged=[{"chapter_id":"ch_01","title":"全文","page_start":1,"page_end":total_pages,"content":"","char_count":0}]
    total_chars = sum(ch["char_count"] for ch in merged)
    result = {"textbook_id":textbook_id,"filename":os.path.basename(filepath),"title":os.path.basename(filepath).replace(".pdf",""),"total_pages":total_pages,"total_chars":total_chars,"chapters":merged}

    os.makedirs(PARSED_DIR, exist_ok=True)
    with open(os.path.join(PARSED_DIR,f"{textbook_id}.json"),"w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    return result
