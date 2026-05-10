"""AI出题 - 基于章节内容生成探索问题"""
from openai import OpenAI
from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

PROMPT = """你是医学教师。基于以下章节摘要，生成4-5个探索性问题引导学生深入学习。
问题类型：
- 概念理解型："xxx的定义是什么？"
- 机制解释型："xxx的过程/机制是怎样的？"
- 对比分析型："xxx和yyy有什么区别？"
- 临床应用型："xxx在临床中如何应用？"

输出JSON数组，每项：{"id":"q1","question":"问题","type":"类型"}
章节摘要：{summary}
直接输出JSON数组："""


def generate_questions(summary_text: str) -> list:
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role":"user","content":PROMPT.format(summary=summary_text[:3000])}],
            temperature=0.7, max_tokens=800, timeout=60
        )
        raw = resp.choices[0].message.content.strip()
        # 提取JSON
        import re, json
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        print(f"出题失败: {e}")
    return [{"id":"q1","question":"本章主要讨论了哪些核心概念？","type":"概念理解"}]
