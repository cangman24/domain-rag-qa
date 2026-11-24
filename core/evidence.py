"""报告生成和校验共用的语料与评测文件哈希。"""
from __future__ import annotations

import hashlib
import os
from typing import BinaryIO, Iterator


def _text_blocks(stream: BinaryIO, chunk: int, newline: bytes | None) -> Iterator[bytes]:
    """转换 CRLF 和 LF，保留其他字节及落在读取边界上的 CR。"""
    carry = b""
    while block := stream.read(chunk):
        block = carry + block
        if newline is not None:
            carry = b"\r" if block.endswith(b"\r") else b""
            if carry:
                block = block[:-1]
            block = block.replace(b"\r\n", b"\n").replace(b"\n", newline)
        yield block
    if carry:
        yield carry


def file_sha256(path: str, chunk: int = 1 << 20, *, newline: bytes | None = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in _text_blocks(stream, chunk, newline):
            h.update(block)
    return h.hexdigest()[:16]


def corpus_sha256(docs_dir: str, *, newline: bytes | None = None) -> tuple[int, str]:
    """按文件名排序，依次输入文件名和内容，沿用当前报告的 16 位指纹。"""
    names = sorted(name for name in os.listdir(docs_dir) if name.endswith(".md"))
    h = hashlib.sha256()
    for name in names:
        h.update(name.encode("utf-8"))
        with open(os.path.join(docs_dir, name), "rb") as stream:
            for block in _text_blocks(stream, 1 << 20, newline):
                h.update(block)
    return len(names), h.hexdigest()[:16]
