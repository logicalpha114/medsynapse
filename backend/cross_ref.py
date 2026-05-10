"""跨书引用 - 找相似章节"""
import json, os
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.config import PARSED_DIR, SUMMARY_DIR, EMBEDDING_MODEL, SIMILARITY_THRESHOLD

embedder = SentenceTransformer(EMBEDDING_MODEL)


def find_related_chapters(book_id: str, chapter_id: str, top_n: int = 5) -> list:
    """找与其他书籍中相似章节"""
    # 加载目标章节摘要
    sp = os.path.join(SUMMARY_DIR, "chapters", f"{book_id}_{chapter_id}.md")
    if not os.path.exists(sp): return []
    with open(sp, "r", encoding="utf-8") as f:
        target_text = f.read()

    # 加载所有其他章节摘要
    others = []
    for fname in os.listdir(os.path.join(SUMMARY_DIR, "chapters")):
        if not fname.endswith(".md"): continue
        bid = fname.split("_")[0]
        if bid == book_id: continue  # 跳过同书
        cid = fname.replace(".md","").replace(f"{bid}_","")
        with open(os.path.join(SUMMARY_DIR, "chapters", fname), "r", encoding="utf-8") as f:
            others.append({"book_id": bid, "chapter_id": cid, "text": f.read()})

    if not others: return []

    # 向量化
    target_emb = embedder.encode([target_text], normalize_embeddings=True)[0]
    other_embs = embedder.encode([o["text"] for o in others], normalize_embeddings=True)

    # 计算相似度
    sims = np.dot(other_embs, target_emb)
    top_idx = np.argsort(sims)[::-1][:top_n]

    results = []
    for idx in top_idx:
        if sims[idx] < SIMILARITY_THRESHOLD: continue
        o = others[idx]
        # 获取书名
        with open(os.path.join(PARSED_DIR, f"{o['book_id']}.json"), "r", encoding="utf-8") as f:
            book = json.load(f)
        # 获取章节标题
        ch_title = ""
        for ch in book.get("chapters", []):
            if ch["chapter_id"] == o["chapter_id"]:
                ch_title = ch["title"]
                break

        results.append({
            "book_id": o["book_id"],
            "book_title": book["title"],
            "chapter_id": o["chapter_id"],
            "chapter_title": ch_title,
            "similarity": round(float(sims[idx]), 3)
        })

    return results
