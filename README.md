# 学科知识整合智能体 · 神经元探索系统

> AI 全栈极速黑客松 - 5小时极限开发

## 项目简介

将7本医学教材抽象为7个"神经元起点"，用户点击神经元展开章节，AI生成引导性探索问题，跨教材关联自动以"突触连接"形式呈现。支持RAG精准问答（带引用来源）、多轮对话、整合报告。

## 功能特性

- 🧠 **神经元探索**：7本教材=7个起点，点击展开章节，游戏化交互
- 🤔 **AI引导问题**：每章自动生成4-5个引导性问题，覆盖4种类型
- 🔗 **跨教材关联**：BGE Embedding自动发现相关章节
- 🔍 **RAG精准问答**：带教材/章节/页码引用
- 💬 **多轮对话**：教师可与系统讨论整合决策
- 📊 **整合报告**：自动生成压缩统计和整合概览

## 环境依赖

- Python 3.10+
- DeepSeek API Key

## 安装步骤

```bash
git clone <repo-url>
cd hacker-med
pip install -r requirements.txt

# 将教材PDF放入 data/textbooks/
# 或在Web界面一键初始化
```

## 配置

环境变量（可选，config.py中已内置默认值）：
```env
DEEPSEEK_API_KEY=sk-your-key
```

## 启动

```bash
cd backend
python main.py
# 访问 http://localhost:8000
```

首次使用：点击页面顶部「⚡一键初始化」自动完成解析→摘要→索引。

## Docker 部署

```bash
docker-compose up -d
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Python |
| PDF解析 | PyMuPDF |
| 大模型 | DeepSeek API (deepseek-v4-pro) |
| 向量嵌入 | BGE-small-zh-v1.5 |
| 向量库 | ChromaDB |
| 前端 | HTML + JS + ECharts |
| 部署 | 魔搭创空间 |

## 文档

- [需求分析](docs/需求分析.md)
- [系统设计](docs/系统设计.md)
- [Agent架构说明](docs/Agent架构说明.md)
- [整合报告](report/整合报告.md)
