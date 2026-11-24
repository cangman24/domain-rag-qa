# -*- coding: utf-8 -*-
"""tests/test_evidence_chain.py —— 数字证据链校验脚本的单测（零依赖）。

覆盖的其实是"证据链会不会被骗过去"：
  · 语料被删 / 被改 → 必须报缺口；
  · 模型名 unknown / 维度不对 → 必须报缺口；
  · 只是新增了文档 → 只提示、不算缺口（报告数字仍对旧范围成立）。
"""
import json
import os
import shutil
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evaluation import EvalItem, save_eval_set  # noqa: E402
from core.evidence import corpus_sha256, file_sha256  # noqa: E402
from tools.verify_evidence_chain import (  # noqa: E402
    check_corpus, check_model, main, verify,
)

_TMP_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp")


def make_tmp() -> str:
    os.makedirs(_TMP_ROOT, exist_ok=True)
    p = os.path.join(_TMP_ROOT, "ev_" + uuid.uuid4().hex[:12])
    os.makedirs(p, exist_ok=True)
    return p


DOC_A = "# 标题A\n\n第一段内容。\n\n第二段内容。"
DOC_B = "# 标题B\n\n另一篇的内容。"


def write_corpus(raw_dir: str, docs=None) -> None:
    os.makedirs(raw_dir, exist_ok=True)
    for name, text in (docs or {"a.md": DOC_A, "b.md": DOC_B}).items():
        with open(os.path.join(raw_dir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


def write_chunks(path: str, docs=None) -> None:
    """按"整篇一个 chunk"写索引——便于精确控制内容比对。"""
    chunks = []
    for name, text in (docs or {"a.md": DOC_A, "b.md": DOC_B}).items():
        chunks.append({"chunk_id": name + "#0", "doc_id": name, "text": text})
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks}, f, ensure_ascii=False)


def write_manifest(run_dir: str, model_info=None, ingest=None) -> str:
    os.makedirs(run_dir, exist_ok=True)
    m = {
        "run_id": os.path.basename(run_dir),
        "timestamp": "2026-10-26 00:00:00",
        "ingest": ingest if ingest is not None else {"embedding_model": "unknown"},
    }
    if model_info is not None:
        m["model_info"] = model_info
    p = os.path.join(run_dir, "eval_manifest.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False)
    return p


GOOD_MODEL = {
    "embedding_model": "models/bge-m3",
    "embedding_dim": 1024,
    "reranker_model": "models/bge-reranker-v2-m3",
    "reranker_loaded": True,
}


class TestCheckCorpus(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = make_tmp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.raw = os.path.join(self.tmp, "raw")
        self.chunks = os.path.join(self.tmp, "chunks.json")

    def test_identical_is_clean(self):
        write_corpus(self.raw)
        write_chunks(self.chunks)
        n_idx, n_cur, notes = check_corpus(self.chunks, self.raw)
        self.assertEqual((n_idx, n_cur), (2, 2))
        self.assertTrue(any(n.startswith("✓ 索引文本块均可在源文档中定位") for n in notes))
        self.assertFalse([n for n in notes if n.startswith("✗")])

    def test_whitespace_only_diff_is_not_drift(self):
        """★ 换行/空格差异不算内容变更——否则全是假阳性。"""
        write_corpus(self.raw)
        write_chunks(self.chunks, {"a.md": DOC_A.replace("\n", "  \n\n"),
                                   "b.md": DOC_B})
        _, _, notes = check_corpus(self.chunks, self.raw)
        self.assertTrue(any(n.startswith("✓ 索引文本块均可在源文档中定位") for n in notes))

    def test_deleted_doc_is_reported(self):
        write_corpus(self.raw)
        write_chunks(self.chunks, {"a.md": DOC_A, "b.md": DOC_B})
        os.remove(os.path.join(self.raw, "b.md"))
        _, _, notes = check_corpus(self.chunks, self.raw)
        self.assertTrue(any("语料已被删除" in n for n in notes))

    def test_edited_content_is_reported(self):
        write_corpus(self.raw)
        write_chunks(self.chunks)
        with open(os.path.join(self.raw, "a.md"), "w", encoding="utf-8") as f:
            # 改写已有句子（而不是追加）：追加时原文仍是子串，本就该判"没变"
            f.write(DOC_A.replace("第一段内容。", "被改写的第一段。"))
        _, _, notes = check_corpus(self.chunks, self.raw)
        self.assertTrue(any(n.startswith("✗ 内容已变更") for n in notes))

    def test_added_doc_is_only_a_note(self):
        write_corpus(self.raw)
        write_chunks(self.chunks, {"a.md": DOC_A, "b.md": DOC_B})
        with open(os.path.join(self.raw, "c.md"), "w", encoding="utf-8") as f:
            f.write("# 新增\n\n新的文档。")
        _, _, notes = check_corpus(self.chunks, self.raw)
        self.assertTrue(any(n.startswith("△ 索引未包含") for n in notes))
        self.assertFalse([n for n in notes if n.startswith("✗")])

    def test_missing_chunks_file_is_only_a_note(self):
        """索引不随仓库分发是设计决定（可 ingest 重建），不该算证据缺口。"""
        write_corpus(self.raw)
        _, _, notes = check_corpus(os.path.join(self.tmp, "nope.json"), self.raw)
        self.assertTrue(any(n.startswith("△ 索引文件不存在") for n in notes))
        self.assertFalse([n for n in notes if n.startswith("✗")])


class TestCheckModel(unittest.TestCase):
    def test_good(self):
        notes = check_model({"model_info": dict(GOOD_MODEL)})
        self.assertFalse([n for n in notes if n.startswith("✗")])
        self.assertTrue(any("embedding_dim = 1024" in n for n in notes))

    def test_unknown_embedding(self):
        notes = check_model({"ingest": {"embedding_model": "unknown"}})
        self.assertTrue(any("无法自证" in n for n in notes))

    def test_wrong_dim(self):
        notes = check_model({"model_info": {**GOOD_MODEL, "embedding_dim": 768}})
        self.assertTrue(any("期望 1024" in n for n in notes))

    def test_missing_dim_is_note_only(self):
        info = {k: v for k, v in GOOD_MODEL.items() if k != "embedding_dim"}
        notes = check_model({"model_info": info})
        self.assertTrue(any(n.startswith("△ embedding_dim 未记录") for n in notes))
        self.assertFalse([n for n in notes if n.startswith("✗")])

    def test_reranker_not_loaded(self):
        notes = check_model({"model_info": {**GOOD_MODEL, "reranker_loaded": False}})
        self.assertTrue(any("reranker_loaded=False" in n for n in notes))

    def test_falls_back_to_ingest_block(self):
        notes = check_model({"ingest": {"embedding_model": "models/bge-m3"}})
        self.assertTrue(any("embedding_model = models/bge-m3" in n for n in notes))


class TestVerify(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = make_tmp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.raw = os.path.join(self.tmp, "raw")
        self.chunks = os.path.join(self.tmp, "chunks.json")
        write_corpus(self.raw)
        write_chunks(self.chunks)

        self.run = os.path.join(self.tmp, "run")
        self.source = os.path.join(self.tmp, "eval.jsonl")
        self.items = [EvalItem("q1", "哪一段？", ["a.md#0"], "第一段")]
        self.snapshot = os.path.join(self.run, "eval_set.jsonl")
        source_item = {**self.items[0].to_dict(), "note": "原始标注"}
        with open(self.source, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(source_item, ensure_ascii=False) + "\n")
        manifest = write_manifest(self.run, GOOD_MODEL)
        save_eval_set(self.items, self.snapshot)
        count, digest = corpus_sha256(self.raw, newline=b"\r\n")
        with open(manifest, "r+", encoding="utf-8") as stream:
            record = json.load(stream)
            record["corpus_fingerprint"] = {
                "doc_count": count, "content_sha256": digest,
                "indexed_doc_count": count, "chunk_count": count,
            }
            record["eval_set"] = {
                "n": len(self.items), "sha256": file_sha256(self.source, newline=b"\r\n"),
            }
            stream.seek(0)
            json.dump(record, stream)
            stream.truncate()

    def verify_fixture(self):
        return verify(self.run, self.chunks, self.raw, self.source)

    def test_complete_chain(self):
        code, res = self.verify_fixture()
        self.assertEqual(code, 0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "passed")
        self.assertEqual(res["indexed_docs"], 2)

    def test_missing_index_leaves_verified_fingerprints_and_pending_index(self):
        os.remove(self.chunks)
        code, res = self.verify_fixture()
        self.assertEqual(code, 0)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "partial")
        self.assertEqual(res["index_status"], "unavailable")
        self.assertTrue(any("语料指纹匹配" in note for note in res["corpus"]))
        self.assertTrue(any("原始评测集指纹匹配" in note for note in res["eval_set"]))

    def test_appending_to_corpus_fails_without_an_index(self):
        os.remove(self.chunks)
        with open(os.path.join(self.raw, "a.md"), "a", encoding="utf-8") as stream:
            stream.write("\n附加文字。")
        code, res = self.verify_fixture()
        self.assertEqual(code, 1)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(any("语料指纹不匹配" in note for note in res["corpus"]))

    def test_mutating_source_sample_fails_without_an_index(self):
        os.remove(self.chunks)
        with open(self.source, "r+", encoding="utf-8") as stream:
            contents = stream.read()
            stream.seek(0)
            stream.write(contents.replace("原始标注", "不同标注"))
            stream.truncate()
        code, res = self.verify_fixture()
        self.assertEqual(code, 1)
        self.assertTrue(any("原始评测集指纹不匹配" in note for note in res["eval_set"]))

    def test_mutating_legacy_snapshot_fails(self):
        save_eval_set([EvalItem("q1", "改了的问题", ["a.md#0"])], self.snapshot)
        code, res = self.verify_fixture()
        self.assertEqual(code, 1)
        self.assertTrue(any("快照与原始评测集" in note for note in res["eval_set"]))

    def test_missing_recorded_snapshot_fails(self):
        os.remove(self.snapshot)
        code, res = self.verify_fixture()
        self.assertEqual(code, 1)
        self.assertTrue(any("报告缺少评测快照" in note for note in res["eval_set"]))

    def test_index_count_mismatch_fails(self):
        write_chunks(self.chunks, {"a.md": DOC_A})
        code, res = self.verify_fixture()
        self.assertEqual(code, 1)
        self.assertEqual(res["index_status"], "failed")
        self.assertTrue(any("索引篇数不匹配" in note for note in res["index"]))

    def test_missing_manifest_returns_two(self):
        code, res = verify(os.path.join(self.tmp, "nope"), self.chunks, self.raw)
        self.assertEqual(code, 2)
        self.assertIn("error", res)

    def test_broken_manifest_returns_two(self):
        run = os.path.join(self.tmp, "run-bad")
        os.makedirs(run, exist_ok=True)
        with open(os.path.join(run, "eval_manifest.json"), "w",
                  encoding="utf-8") as f:
            f.write("{ not json")
        code, _ = verify(run, self.chunks, self.raw)
        self.assertEqual(code, 2)

    def test_corpus_drift_fails(self):
        run = os.path.join(self.tmp, "run-2")
        write_manifest(run, GOOD_MODEL)
        os.remove(os.path.join(self.raw, "a.md"))
        code, res = verify(run, self.chunks, self.raw)
        self.assertEqual(code, 1)
        self.assertFalse(res["ok"])


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = make_tmp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.raw = os.path.join(self.tmp, "raw")
        self.chunks = os.path.join(self.tmp, "chunks.json")
        write_corpus(self.raw)
        write_chunks(self.chunks)
        self.run = os.path.join(self.tmp, "run-1")
        write_manifest(self.run, GOOD_MODEL)

    def test_main_ok(self):
        self.assertEqual(main([self.run, "--chunks", self.chunks,
                               "--raw", self.raw]), 0)

    def test_main_gap(self):
        write_manifest(self.run, {**GOOD_MODEL, "embedding_model": "unknown"})
        self.assertEqual(main([self.run, "--chunks", self.chunks,
                               "--raw", self.raw]), 1)

    def test_main_json(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([self.run, "--chunks", self.chunks, "--raw", self.raw,
                         "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["run_id"], "run-1")


if __name__ == "__main__":
    unittest.main()
