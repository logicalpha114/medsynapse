"""RAG引擎 - 向量检索 + 生成回答"""
import json, os, chromadb
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from backend.config import (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, CHUNK_SIZE, CHUNK_OVERLAP,
                    TOP_K_RETRIEVAL, EMBEDDING_MODEL, PARSED_DIR, SUMMARY_DIR, VECTOR_DIR)

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
embedder = SentenceTransformer(EMBEDDING_MODEL)
os.makedirs(VECTOR_DIR, exist_ok=True)
chroma = chromadb.PersistentClient(path=VECTOR_DIR)

ANSWER_PROMPT = """基于以下教材内容回答问题。必须：
1. 只用提供的上下文
2. 引用格式：[教材名, 第X章, 第X页]
3. 找不到就说"未找到相关信息"

上下文：{context}
问题：{question}
回答："""


def build_index():
    """建立向量索引（原文chunk + 章节摘要）"""
    try: chroma.delete_collection("synapse")
    except: pass
    col = chroma.create_collection("synapse", metadata={"hnsw:space":"cosine"})

    all_chunks = []
    for fname in os.listdir(PARSED_DIR):
        if not fname.endswith(".json"): continue
        tid = fname.replace(".json","")
        with open(os.path.join(PARSED_DIR, fname), "r", encoding="utf-8") as f:
            book = json.load(f)

        for ch in book["chapters"]:
            # 原文分块
            text = ch["content"]
            start = 0
            ci = 0
            while start < len(text):
                end = start + CHUNK_SIZE
                chunk = text[start:end]
                # 找最近的句号/换行切断
                if end < len(text):
                    for sep in ["\n", "。", "；", ". "]:
                        p = chunk.rfind(sep)
                        if p > CHUNK_SIZE//2: end = start+p+1; break
                all_chunks.append({
                    "id": f"{tid}_{ch['chapter_id']}_c{ci}",
                    "text": text[start:end],
                    "meta": {"textbook": book["title"], "chapter": ch["title"],
                             "page": ch["page_start"]+start//CHUNK_SIZE, "type": "chunk"}
                })
                start = end - CHUNK_OVERLAP if end - CHUNK_OVERLAP > start else end
                ci += 1

        # 章节摘要
        for ch in book["chapters"]:
            sp = os.path.join(SUMMARY_DIR, "chapters", f"{tid}_{ch['chapter_id']}.md")
            if os.path.exists(sp):
                with open(sp, "r", encoding="utf-8") as f:
                    all_chunks.append({
                        "id": f"{tid}_{ch['chapter_id']}_summary",
                        "text": f.read(),
                        "meta": {"textbook": book["title"], "chapter": ch["title"],
                                 "page": ch["page_start"], "type": "chapter_summary"}
                    })

    # 分批向量化
    bs = 200
    for i in range(0, len(all_chunks), bs):
        batch = all_chunks[i:i+bs]
        col.add(embeddings=embedder.encode([c["text"] for c in batch], normalize_embeddings=True).tolist(),
                documents=[c["text"] for c in batch],
                metadatas=[c["meta"] for c in batch],
                ids=[c["id"] for c in batch])

    return len(all_chunks)


def ask(question: str) -> dict:
    """RAG问答"""
    try: col = chroma.get_collection("synapse")
    except: return {"answer":"请先建立索引","citations":[]}

    q_emb = embedder.encode([question], normalize_embeddings=True).tolist()
    results = col.query(query_embeddings=q_emb, n_results=TOP_K_RETRIEVAL)

    contexts, citations = [], []
    for i in range(len(results["ids"][0])):
        cid = results["ids"][0][i]
        if cid in citations: continue
        contexts.append(results["documents"][0][i])
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        citations.append({
            "textbook": meta.get("textbook",""),
            "chapter": meta.get("chapter",""),
            "page": meta.get("page",0),
            "score": round(1-dist, 3),
            "chunk_preview": results["documents"][0][i][:200]
        })

    if not contexts:
        return {"answer":"当前知识库中未找到相关信息","citations":[]}

    ctx = "\n\n---\n\n".join(contexts)[:5000]
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role":"user","content":ANSWER_PROMPT.format(context=ctx, question=question)}],
            temperature=0.2, max_tokens=1000, timeout=60
        )
        return {"answer": resp.choices[0].message.content, "citations": citations[:TOP_K_RETRIEVAL]}
    except:
        return {"answer":"生成回答失败","citations": citations[:TOP_K_RETRIEVAL]}
