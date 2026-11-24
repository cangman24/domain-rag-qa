"""迁移回归覆盖延迟注解及诊断工具的正常命令入口。"""
import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.mcp import ToolRegistry
from tools import calibrate_threshold, diagnose_refusal, diagnose_refusal2, verify_prompt_fix


class TestMigrationGaps(unittest.TestCase):
    def test_deferred_annotations_keep_integer_tool_arguments(self):
        namespace = {}
        exec("from __future__ import annotations\n"
             "def search(query: str, top_k: int = 3, enabled: bool = True):\n"
             "    return top_k, enabled\n", namespace)
        registry = ToolRegistry()
        registry.tool()(namespace["search"])
        props = registry.get("search").input_schema["properties"]
        self.assertEqual(props["top_k"]["type"], "integer")
        self.assertEqual(props["enabled"]["type"], "boolean")
        self.assertEqual(registry.call("search", {"query": "test", "top_k": 5}), (5, True))

    def test_diagnostic_commands_write_reports_to_requested_output(self):
        for module in (calibrate_threshold, diagnose_refusal, diagnose_refusal2, verify_prompt_fix):
            with self.subTest(tool=module.__name__), TemporaryDirectory() as temporary:
                source = Path(temporary) / "eval.jsonl"
                out = Path(temporary) / "reports" / "result.json"
                items = [
                    {"qid": "q1", "query": "精度", "gold_ids": ["c1"], "is_answerable": True},
                    {"qid": "q2", "query": "越界", "gold_ids": [], "is_answerable": False},
                ]
                source.write_text("\n".join(json.dumps(item) for item in items), encoding="utf-8")
                service = SimpleNamespace(llm=object())
                service.retrieve = lambda query: SimpleNamespace(scores=[1.0 if query == "精度" else -1.0])
                # 让定向复测工具先发现拒答样本，再在第二遍观察到作答。
                answers = iter((
                    SimpleNamespace(answer="知识库中未找到", refused=True,
                                    hits=[{"chunk_id": "c1", "score": 1.0}]),
                    SimpleNamespace(answer="知识库中未找到", refused=True, hits=[]),
                    SimpleNamespace(answer="精度要求 [1]", refused=False,
                                    hits=[{"chunk_id": "c1", "score": 1.0}]),
                ))
                if module is verify_prompt_fix:
                    sequence = iter((
                        SimpleNamespace(answer="知识库中未找到", refused=True,
                                        hits=[{"chunk_id": "c1", "score": 1.0}]),
                        SimpleNamespace(answer="精度要求 [1]", refused=False,
                                        hits=[{"chunk_id": "c1", "score": 1.0}]),
                    ))
                    service.answer = lambda query, results=sequence: next(results)
                else:
                    service.answer = lambda query, results=answers: next(results)
                with patch.object(module, "build_production_service", return_value=service), \
                        patch("sys.argv", [module.__file__, str(source), "--out", str(out)]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(), 0)
                self.assertIsInstance(json.loads(out.read_text(encoding="utf-8")), dict)
