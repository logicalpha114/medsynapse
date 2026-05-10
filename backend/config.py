"""配置 - 神经元探索系统"""
import os
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-1a7612c9e30747dab1b150cd3a759f8f")
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-v4-pro"

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
TOP_K_RETRIEVAL = 5
SIMILARITY_THRESHOLD = 0.6

DATA_DIR = os.path.join(_BASE, "data")
TEXTBOOK_DIR = os.path.join(DATA_DIR, "textbooks")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
SUMMARY_DIR = os.path.join(DATA_DIR, "summaries")
VECTOR_DIR = os.path.join(DATA_DIR, "vector_db")
