# -*- coding: utf-8 -*-
"""core —— 领域 RAG 问答的共享基建。

本包 18 个模块中 **16 个只用标准库**，外部依赖只出现在 4 处，边界清晰：

    core/embedder / core/reranker  -> 导入即需要 torch / transformers（真模型层）
    core/vectorstore.ChromaVectorStore      -> 延迟导入，需要 chromadb
    core.llm.LLMClient 的默认 transport     -> 延迟导入，需要 openai
    core.loaders 的 pdf / docx 解析          -> 延迟导入，需要 pypdf / python-docx

因此 tests/ 的全部用例在裸 Python 上全绿（约 1 秒），CI 不需要装 torch。
embedder / reranker 不在"零依赖"范围内是刻意的：它们封装的就是真模型，
其行为必须由真机验证（本仓库的 cli/eval 命令即真机入口），
不该混进离线单测的职责里。
"""

__all__ = [
    "agent",
    "bm25",
    "embedder",
    "eval_runner",
    "evaluation",
    "ingest",
    "judge",
    "llm",
    "loaders",
    "mcp",
    "metrics",
    "pipeline",
    "reranker",
    "retrieval",
    "service",
    "sse",
    "text",
    "vectorstore",
]
