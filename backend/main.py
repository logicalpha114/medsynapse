"""
神经元探索系统 - FastAPI 主应用
7本教材 = 7个起点神经元，点击展开章节，AI出题引导探索
"""
import os, sys, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import TEXTBOOK_DIR, PARSED_DIR, SUMMARY_DIR, VECTOR_DIR, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from backend.pdf_parser import parse_pdf
from backend.summary_builder import build_all_summaries
from backend.question_gen import generate_questions
from backend.rag_engine import build_index, ask
from backend.cross_ref import find_related_chapters
from openai import OpenAI

llm = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

# 对话历史
dialogue_history = []

app = FastAPI(title="神经元探索系统")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for d in [TEXTBOOK_DIR, PARSED_DIR, SUMMARY_DIR+"/chapters", SUMMARY_DIR+"/books", VECTOR_DIR]:
    os.makedirs(d, exist_ok=True)

# 全局状态
state = {"parsed": [], "summarized": False, "indexed": False, "explore_path": []}


# ===== 教材管理 =====
@app.get("/api/books")
def list_books():
    """列出所有教材及其章节结构"""
    books = []
    for fname in sorted(os.listdir(PARSED_DIR)):
        if not fname.endswith(".json"): continue
        tid = fname.replace(".json","")
        with open(os.path.join(PARSED_DIR, fname), "r", encoding="utf-8") as f:
            book = json.load(f)
        # 检查摘要状态
        has_summary = os.path.exists(os.path.join(SUMMARY_DIR, "books", f"{tid}_overview.md"))
        chapters = []
        for ch in book["chapters"]:
            ch_has_summary = os.path.exists(os.path.join(SUMMARY_DIR, "chapters", f"{tid}_{ch['chapter_id']}.md"))
            chapters.append({
                "chapter_id": ch["chapter_id"],
                "title": ch["title"].replace("\n",""),
                "page_start": ch["page_start"],
                "page_end": ch["page_end"],
                "char_count": ch["char_count"],
                "has_summary": ch_has_summary
            })
        books.append({
            "textbook_id": tid,
            "title": book["title"],
            "total_pages": book["total_pages"],
            "total_chars": book["total_chars"],
            "chapters": chapters,
            "has_summary": has_summary
        })
    return {"books": books, "count": len(books), "summarized": state["summarized"], "indexed": state["indexed"]}


@app.post("/api/books/upload")
async def upload(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".",1)[-1].lower()
    if ext not in ["pdf","md","txt","docx"]: raise HTTPException(400, f"不支持格式: {ext}")

    n = len([f for f in os.listdir(PARSED_DIR) if f.endswith(".json")])
    tid = f"book_{n+1:02d}"
    path = os.path.join(TEXTBOOK_DIR, f"{tid}_{file.filename}")
    with open(path, "wb") as f: f.write(await file.read())

    return {"textbook_id": tid, "filename": file.filename, "status": "uploaded"}


@app.post("/api/books/{tid}/parse")
def parse(tid: str):
    """解析教材"""
    files = [f for f in os.listdir(TEXTBOOK_DIR) if f.startswith(tid)]
    if not files: raise HTTPException(404, "教材文件不存在")
    result = parse_pdf(os.path.join(TEXTBOOK_DIR, files[0]), tid)
    if tid not in state["parsed"]: state["parsed"].append(tid)
    return {"status": "parsed", "chapters": len(result["chapters"]), "total_chars": result["total_chars"]}


@app.post("/api/books/parse-all")
def parse_all():
    """一键解析所有已上传教材"""
    results = []
    for fname in os.listdir(TEXTBOOK_DIR):
        if not fname.endswith(".pdf"): continue
        n = len(results) + 1
        tid = f"book_{n:02d}"
        # 检查是否已解析
        if os.path.exists(os.path.join(PARSED_DIR, f"{tid}.json")):
            results.append({"textbook_id": tid, "status": "already_parsed"})
            continue
        try:
            r = parse_pdf(os.path.join(TEXTBOOK_DIR, fname), tid)
            state["parsed"].append(tid)
            results.append({"textbook_id": tid, "title": r["title"], "status": "parsed", "chapters": len(r["chapters"])})
        except Exception as e:
            results.append({"textbook_id": tid, "status": "failed", "error": str(e)})
    return {"results": results}


@app.post("/api/books/summarize-all")
def summarize():
    """一键生成所有摘要"""
    result = build_all_summaries()
    state["summarized"] = True
    return result


@app.post("/api/books/index-all")
def index():
    """一键建立向量索引"""
    count = build_index()
    state["indexed"] = True
    return {"chunks": count, "status": "indexed"}


# ===== 探索功能 =====
@app.get("/api/explore/{tid}/{cid}")
def explore_chapter(tid: str, cid: str):
    """点击章节：返回摘要 + AI生成问题 + 跨书引用"""
    # 读取章节摘要MD
    sp = os.path.join(SUMMARY_DIR, "chapters", f"{tid}_{cid}.md")
    summary = ""
    if os.path.exists(sp):
        with open(sp, "r", encoding="utf-8") as f:
            summary = f.read()

    # AI出题
    questions = generate_questions(summary) if summary else []

    # 跨书引用
    refs = find_related_chapters(tid, cid)

    # 记录探索路径
    book_title = ""
    ch_title = ""
    pp = os.path.join(PARSED_DIR, f"{tid}.json")
    if os.path.exists(pp):
        with open(pp, "r", encoding="utf-8") as f:
            book = json.load(f)
        book_title = book["title"]
        for ch in book["chapters"]:
            if ch["chapter_id"] == cid:
                ch_title = ch["title"].replace("\n","")
                break

    state["explore_path"].append({
        "book_id": tid, "book_title": book_title,
        "chapter_id": cid, "chapter_title": ch_title,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    })

    return {
        "book_title": book_title,
        "chapter_title": ch_title,
        "summary": summary,
        "questions": questions,
        "cross_refs": refs,
        "explore_path": state["explore_path"][-20:]  # 最近20步
    }


# ===== 问答 =====
@app.post("/api/ask")
def ask_question(payload: dict = Body(...)):
    """RAG问答"""
    q = payload.get("question","")
    if not q: raise HTTPException(400, "问题为空")
    return ask(q)


# ===== 探索路径 =====
@app.get("/api/path")
def get_path():
    return {"path": state["explore_path"]}


# ===== 对话 =====
@app.post("/api/dialogue")
def dialogue(payload: dict = Body(...)):
    """多轮对话 - 教师与系统讨论整合方案"""
    msg = payload.get("message", "")
    if not msg: raise HTTPException(400, "消息为空")
    dialogue_history.append({"role": "user", "content": msg})
    try:
        resp = llm.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role":"system","content":"你是医学知识整合助手。帮助教师理解跨教材知识点整合结果。"},
                *dialogue_history[-10:]
            ], temperature=0.5, max_tokens=800, timeout=60
        )
        reply = resp.choices[0].message.content
        dialogue_history.append({"role":"assistant","content":reply})
        return {"reply": reply, "history_length": len(dialogue_history)}
    except Exception as e:
        return {"reply": f"对话出错: {e}", "history_length": len(dialogue_history)}

@app.get("/api/dialogue/history")
def dialogue_history_endpoint():
    return {"history": dialogue_history}


# ===== 整合报告 =====
@app.get("/api/report")
def report():
    """生成整合报告数据"""
    books = []
    total_chars = 0
    total_chapters = 0
    for fn in sorted(os.listdir(PARSED_DIR)):
        if not fn.endswith(".json"): continue
        with open(os.path.join(PARSED_DIR, fn), "r", encoding="utf-8") as f:
            b = json.load(f)
        books.append({"title": b["title"], "pages": b["total_pages"], "chapters": len(b["chapters"]), "chars": b["total_chars"]})
        total_chars += b["total_chars"]
        total_chapters += len(b["chapters"])

    summary_count = len([f for f in os.listdir(os.path.join(SUMMARY_DIR, "chapters")) if f.endswith(".md")])

    return {
        "summary": {
            "textbook_count": len(books),
            "total_chapters": total_chapters,
            "total_chars": total_chars,
            "chapter_summaries": summary_count,
            "compression_note": "通过章节摘要预生成实现知识浓缩，单章300字摘要 = 原始字数的1-5%"
        },
        "books": books,
        "explore_path_length": len(state["explore_path"]),
        "indexed": state["indexed"],
        "system_note": "基于神经元探索模型：7本教材作为7个起点，用户通过AI引导问题深度探索各章节，跨书引用自动关联相关知识点。"
    }


# ===== 系统状态 =====
@app.get("/api/status")
def status():
    parsed = len([f for f in os.listdir(PARSED_DIR) if f.endswith(".json")])
    summaries = len([f for f in os.listdir(os.path.join(SUMMARY_DIR, "chapters")) if f.endswith(".md")])
    return {"parsed_books": parsed, "chapter_summaries": summaries, "indexed": state["indexed"]}


# 静态文件 - 挂载到 /static，根路径单独处理
frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend):
    from fastapi.responses import FileResponse
    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend, "index.html"))
    app.mount("/static", StaticFiles(directory=frontend), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
