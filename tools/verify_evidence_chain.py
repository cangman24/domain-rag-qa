# -*- coding: utf-8 -*-
"""对照评测报告重算语料与评测集指纹，并核对可用的索引和模型记录。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Callable, Dict, List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.evaluation import eval_set_lines, load_eval_set  # noqa: E402
from core.evidence import corpus_sha256, file_sha256  # noqa: E402

EXPECTED_DIM = 1024
LINE_ENDINGS = ((None, "原始字节"), (b"\r\n", "CRLF"), (b"\n", "LF"))
RESULT_LABELS = {
    "passed": "校验通过",
    "partial": "部分校验通过，仍有未核验项",
    "failed": "校验失败",
}


def _fingerprint_note(label: str, expected: str,
                      compute: Callable[[bytes | None], str]) -> str:
    actual = ""
    for newline, mode in LINE_ENDINGS:
        digest = compute(newline)
        if newline is None:
            actual = digest
        if digest == expected:
            return f"✓ {label}指纹匹配：{digest}（{mode}）"
    return f"✗ {label}指纹不匹配：报告 {expected}，当前 {actual}（LF/CRLF 均不匹配）"


def check_raw(raw_dir: str, expected: Dict[str, Any]) -> List[str]:
    recorded = expected.get("content_sha256")
    if not recorded:
        return ["△ manifest 缺少语料指纹，无法校验原始语料版本"]
    try:
        count, digest = corpus_sha256(raw_dir)
        notes = [_fingerprint_note("语料", recorded, lambda newline:
                                   digest if newline is None
                                   else corpus_sha256(raw_dir, newline=newline)[1])]
    except OSError as exc:
        return [f"✗ 无法读取语料目录 {raw_dir}：{exc}"]
    if "doc_count" in expected and count != expected["doc_count"]:
        notes.append(f"✗ 语料篇数不匹配：报告 {expected['doc_count']}，当前 {count}")
    else:
        notes.append(f"语料篇数：{count}")
    return notes


def _eval_source(meta: Dict[str, Any]) -> str | None:
    candidate_paths = []
    for key in ("path_rel", "path"):
        recorded = meta.get(key)
        if not isinstance(recorded, str) or not recorded:
            continue
        relative = recorded.replace("\\", "/")
        if not relative.startswith("/") and ":" not in relative:
            candidate = os.path.abspath(os.path.join(ROOT, relative))
            if os.path.commonpath((ROOT, candidate)) == ROOT:
                if os.path.isfile(candidate):
                    return candidate
                candidate_paths.append(candidate)
    return next(iter(candidate_paths), None)


def check_eval_set(run_dir: str, meta: Dict[str, Any],
                   eval_set_path: str | None) -> List[str]:
    snapshot = os.path.join(run_dir, "eval_set.jsonl")
    source = eval_set_path or _eval_source(meta)
    recorded = meta.get("sha256")
    snapshot_sha = meta.get("snapshot_sha256")
    notes = []

    try:
        if recorded and source:
            notes.append(_fingerprint_note("原始评测集", recorded,
                                           lambda newline: file_sha256(source, newline=newline)))
        elif recorded:
            notes.append("△ 无法定位原始评测集，请用 --eval-set 指定路径")
        elif source or not snapshot_sha:
            notes.append("△ manifest 缺少原始评测集指纹")

        if snapshot_sha:
            notes.append(_fingerprint_note("评测快照", snapshot_sha,
                                           lambda newline: file_sha256(snapshot, newline=newline)))
        elif not os.path.isfile(snapshot):
            prefix = "✗" if recorded else "△"
            notes.append(f"{prefix} 报告缺少评测快照，无法核验快照")
            return notes

        items = load_eval_set(snapshot)
        if "n" in meta and len(items) != meta["n"]:
            notes.append(f"✗ 评测快照条数不匹配：报告 {meta['n']}，快照 {len(items)}")
        if source and (recorded or os.path.isfile(source)):
            original = load_eval_set(source)
            same = original == items
            if not snapshot_sha and same:
                with open(snapshot, encoding="utf-8") as stream:
                    same = stream.read() == "".join(eval_set_lines(original))
            if not same:
                notes.append("✗ 评测快照与原始评测集的评测字段不一致")
            else:
                notes.append(f"✓ 评测快照与原始评测集的 {len(items)} 条评测字段一致")
        elif not snapshot_sha:
            notes.append("△ 历史评测快照无独立指纹，且缺少原始评测集对照")
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        notes.append(f"✗ 无法读取评测集或快照：{exc}")
    return notes


def check_corpus(chunks_path: str, raw_dir: str,
                 expected: Dict[str, Any] | None = None) -> Tuple[int, int, List[str]]:
    """验证现有索引的文本块及记录的篇数和块数。"""
    cur = {name for name in os.listdir(raw_dir) if name.endswith(".md")} \
        if os.path.isdir(raw_dir) else set()
    if not os.path.exists(chunks_path):
        return 0, len(cur), [f"△ 索引文件不存在：{chunks_path}，无法验证索引"]

    with open(chunks_path, encoding="utf-8") as stream:
        index = json.load(stream)
    chunks = index.get("chunks") if isinstance(index, dict) else None
    if not isinstance(chunks, list) or not chunks:
        return 0, len(cur), ["✗ 索引缺少有效的 chunks 列表"]

    by: Dict[str, List[str]] = {}
    for chunk in chunks:
        if (not isinstance(chunk, dict) or not isinstance(chunk.get("doc_id"), str)
                or not chunk["doc_id"] or not isinstance(chunk.get("text"), str)
                or not chunk["text"].strip()):
            return 0, len(cur), ["✗ 索引含缺少 doc_id 或文本的块"]
        by.setdefault(chunk["doc_id"], []).append(chunk["text"])

    notes = [f"索引 {len(by)} 篇 / 当前 {len(cur)} 篇 / {len(chunks)} 块"]
    drift = sorted(set(by) - cur)
    added = sorted(cur - set(by))
    if drift:
        notes.append(f"✗ 语料已被删除或索引文档名无效：{drift}")
    if added:
        notes.append(f"△ 索引未包含（报告数字不含这些文档）：{added}")

    bad = []
    for doc in sorted(set(by) & cur):
        with open(os.path.join(raw_dir, doc), encoding="utf-8") as stream:
            text = re.sub(r"\s+", "", stream.read())
        if any(re.sub(r"\s+", "", chunk) not in text for chunk in by[doc]):
            bad.append(doc)
    if bad:
        notes.append(f"✗ 内容已变更：{bad}")
    elif not drift:
        notes.append("✓ 索引文本块均可在源文档中定位（忽略空白）")

    expected = expected or {}
    for field, label, count in (("indexed_doc_count", "索引篇数", len(by)),
                                ("chunk_count", "索引块数", len(chunks))):
        if field in expected and count != expected[field]:
            notes.append(f"✗ {label}不匹配：报告 {expected[field]}，当前 {count}")
    return len(by), len(cur), notes


def check_model(manifest: Dict[str, Any]) -> List[str]:
    """检查 manifest 中的模型标识和维度记录。"""
    out: List[str] = []
    info = manifest.get("model_info") or {}
    ing = manifest.get("ingest") or {}
    emb = info.get("embedding_model") or ing.get("embedding_model")
    dim = info.get("embedding_dim")
    rr = info.get("reranker_model")

    if emb in (None, "", "unknown"):
        out.append("✗ embedding_model 缺失/为 unknown → 模型归属无法自证")
    else:
        out.append(f"✓ embedding_model = {emb}")

    if dim is None:
        out.append("△ embedding_dim 未记录（重跑后由脚本实测写入）")
    elif dim not in (EXPECTED_DIM, str(EXPECTED_DIM)):
        out.append(f"✗ embedding_dim = {dim}，期望 {EXPECTED_DIM}")
    else:
        out.append(f"✓ embedding_dim = {dim}")

    if rr in (None, "", "unknown"):
        out.append("△ reranker_model 未记录（无法自证精排是否加载）")
    else:
        out.append(f"✓ reranker_model = {rr}")
        if info.get("reranker_loaded") is False:
            out.append("✗ reranker_loaded=False → 本次 run 没有精排")
    return out


def verify(run_dir: str, chunks_path: str, raw_dir: str,
           eval_set_path: str | None = None) -> Tuple[int, Dict[str, Any]]:
    """退出码 0 表示无失败项，1 表示证据有缺口，2 表示 manifest 无法使用。"""
    manifest_path = os.path.join(run_dir, "eval_manifest.json")
    try:
        with open(manifest_path, encoding="utf-8") as stream:
            manifest = json.load(stream)
        if not isinstance(manifest, dict) or any(
            field in manifest and not isinstance(manifest[field], dict)
            for field in ("eval_set", "corpus_fingerprint", "model_info", "ingest")
        ):
            raise ValueError("manifest 或证据字段不是 JSON 对象")
    except (OSError, ValueError) as exc:
        return 2, {"error": f"无法读取 manifest {manifest_path}：{exc}"}

    expected = manifest.get("corpus_fingerprint") or {}
    corpus_notes = check_raw(raw_dir, expected)
    eval_notes = check_eval_set(run_dir, manifest.get("eval_set") or {}, eval_set_path)
    try:
        n_idx, n_cur, index_notes = check_corpus(chunks_path, raw_dir, expected)
    except (OSError, ValueError) as exc:
        n_idx, n_cur, index_notes = 0, 0, [f"✗ 无法读取索引或对照语料：{exc}"]
    if any(note.startswith("✗") for note in index_notes):
        index_status = "failed"
    elif not os.path.exists(chunks_path):
        index_status = "unavailable"
    elif any(note.startswith("△") for note in index_notes):
        index_status = "partial"
    else:
        index_status = "passed"

    model_notes = check_model(manifest)
    notes = corpus_notes + eval_notes + index_notes + model_notes
    failed = any(note.startswith("✗") for note in notes)
    partial = any(note.startswith("△") for note in notes)
    status = "failed" if failed else "partial" if partial else "passed"

    return (1 if failed else 0), {
        "run_id": manifest.get("run_id"),
        "timestamp": manifest.get("timestamp"),
        "corpus": corpus_notes,
        "eval_set": eval_notes,
        "index": index_notes,
        "index_status": index_status,
        "model": model_notes,
        "indexed_docs": n_idx,
        "current_docs": n_cur,
        "status": status,
        "ok": status == "passed",
    }


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="评测报告数字证据链校验")
    p.add_argument("run_dir", nargs="?", default="reports/latest",
                   help="run 目录（含 eval_manifest.json）")
    p.add_argument("--chunks", default=os.path.join(ROOT, "data/vectors/chunks.json"))
    p.add_argument("--raw", default=os.path.join(ROOT, "data/raw"))
    p.add_argument("--eval-set", help="指定原始评测集路径，覆盖 manifest 中的路径")
    p.add_argument("--json", action="store_true", help="输出 JSON（给 CI 用）")
    args = p.parse_args(argv)

    code, res = verify(args.run_dir, args.chunks, args.raw, args.eval_set)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return code
    if "error" in res:
        print(f"[error] {res['error']}", file=sys.stderr)
        return code
    print(f"[run] {res['run_id']} @ {res['timestamp']}")
    for section in ("corpus", "eval_set", "index", "model"):
        print(f"[{section}]")
        for note in res[section]:
            print("  " + note)
    print(f"[result] {RESULT_LABELS[res['status']]}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
