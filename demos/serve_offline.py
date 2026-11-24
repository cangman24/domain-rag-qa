"""Run the offline demonstration corpus behind the normal RAG HTTP API."""
import argparse
import os
from pathlib import Path
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import RetrievalConfig
from core.service import RagService, ServiceConfig
from core.store import ChatStore
from kb_qa.api_fastapi import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 RAG 离线体验服务")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--llm", action="store_true",
                        help="使用 .env 中配置的模型生成回答，检索仍使用演示语料与哈希嵌入")
    args = parser.parse_args()

    import uvicorn

    demo = runpy.run_path(str(Path(__file__).with_name("demo_ingest.py")))
    index = demo["res"]
    llm = None
    if args.llm:
        from core.llm import LLMClient
        from kb_qa.bootstrap import load_env_file

        load_env_file()
        if not os.environ.get("DEEPSEEK_API_KEY"):
            parser.error("真实模型模式需要在 .env 配置 DEEPSEEK_API_KEY")
        llm = LLMClient(api_key=os.environ["DEEPSEEK_API_KEY"],
                        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                        max_retries=1, timeout=45)
    service = RagService(
        retriever=demo["retriever"],
        llm=llm,
        doc_lookup=index.doc_text,
        meta_lookup=index.metadata_for,
        retrieval_config=RetrievalConfig(use_vector=True, use_bm25=True, use_rerank=True, top_k=3),
        config=ServiceConfig(top_k=3, refusal_threshold=0.0),
    )
    store = ChatStore(str(Path(demo["RUNTIME_DIR"]) / "offline-chat.sqlite3"))
    app = build_app(service, title="Domain RAG QA · Offline demo", store=store)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
