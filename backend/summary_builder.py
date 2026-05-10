"""章节摘要生成 - 预生成每章300字MD摘要"""
import json, os
from openai import OpenAI
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, PARSED_DIR, SUMMARY_DIR

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

PROMPT = """用300字概括以下医学教材章节，包含：3-5个核心知识点、主要内容脉络、关键概念。
章节：{title}
内容：{content}
直接输出Markdown摘要："""

def build_all_summaries(textbook_ids: list[str] = None):
    """为所有教材生成章节摘要MD"""
    os.makedirs(os.path.join(SUMMARY_DIR, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(SUMMARY_DIR, "books"), exist_ok=True)

    if textbook_ids is None:
        textbook_ids = [f.replace(".json","") for f in os.listdir(PARSED_DIR) if f.endswith(".json")]

    all_chapters = []
    for tid in textbook_ids:
        with open(os.path.join(PARSED_DIR, f"{tid}.json"), "r", encoding="utf-8") as f:
            book = json.load(f)

        ch_summaries = []
        for ch in book["chapters"]:
            content = ch["content"]
            if len(content) > 4000:
                content = content[:2000] + "\n...(中略)...\n" + content[-2000:]

            try:
                resp = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role":"user","content":PROMPT.format(title=ch["title"], content=content)}],
                    temperature=0.3, max_tokens=800, timeout=90
                )
                summary = resp.choices[0].message.content
            except Exception:
                summary = f"## {ch['title']}\n\n本章共{ch['char_count']}字，覆盖第{ch['page_start']}-{ch['page_end']}页。"

            # 保存
            path = os.path.join(SUMMARY_DIR, "chapters", f"{tid}_{ch['chapter_id']}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {book['title']} - {ch['title']}\n\n{summary}\n\n> 页码: {ch['page_start']}-{ch['page_end']} | 字数: {ch['char_count']}")

            ch_summaries.append({
                "chapter_id": ch["chapter_id"],
                "title": ch["title"],
                "summary": summary,
                "page_start": ch["page_start"],
                "page_end": ch["page_end"],
                "char_count": ch["char_count"],
                "textbook_id": tid,
                "textbook_title": book["title"]
            })
            all_chapters.append(ch_summaries[-1])

        # 书级摘要
        joined = "\n\n".join([s["summary"] for s in ch_summaries])
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role":"user","content":f"基于以下各章摘要，写一个200字全书概览，列出最核心的8-10个知识点：\n\n{joined[:4000]}"}],
                temperature=0.3, max_tokens=600, timeout=60
            )
            book_summary = resp.choices[0].message.content
        except Exception:
            book_summary = f"《{book['title']}》共{len(book['chapters'])}章，{book['total_chars']}字。"

        with open(os.path.join(SUMMARY_DIR, "books", f"{tid}_overview.md"), "w", encoding="utf-8") as f:
            f.write(f"# 《{book['title']}》概览\n\n{book_summary}")

    return {"chapters": len(all_chapters), "books": len(textbook_ids)}
