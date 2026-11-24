"""即使已有 API Key，本地检索模式也不装配远程模型。"""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from kb_qa.bootstrap import build_production_service


class TestLocalMode(unittest.TestCase):
    def test_local_mode_does_not_create_llm_client(self):
        embedder = SimpleNamespace(encode_one=lambda text: [1.0])
        reranker = SimpleNamespace(rerank=lambda query, pairs: pairs)
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-only"}), \
                patch("kb_qa.bootstrap.load_env_file"), \
                patch("kb_qa.bootstrap.build_embedder_and_reranker",
                      return_value=(embedder, reranker)), \
                patch("kb_qa.bootstrap.build_or_load_index",
                      return_value=(None, None, lambda cid: "", {})), \
                patch("kb_qa.bootstrap.LLMClient") as client:
            service = build_production_service(use_llm=False)
        self.assertIsNone(service.llm)
        client.assert_not_called()
