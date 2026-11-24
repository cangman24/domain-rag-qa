# reports/ —— 评测报告

> **`latest/` 是当前唯一的权威报告；`archive/` 是调参历史。**
> 数字一律引用 `latest/`，历史 run 只用来回答"为什么参数是现在这个值"。

每个 run 目录（含 `latest/`）是一次完整评测的产物：

| 文件 | 内容 |
|---|---|
| `eval_manifest.json` | **运行指纹**：run_id、时间、评测集 sha256、切分参数与配置指纹、检索口径、评委信息，以及 `model_info`（模型实测）与 `corpus_fingerprint`（语料指纹） |
| `eval_set.jsonl` | 本次参与评测的字段快照。新报告记录独立的 `eval_set.snapshot_sha256` |
| `retrieval_A~D_*.md` | 四档消融的逐档报告（指标表 + 分类型统计 + Badcase 清单） |
| `SUMMARY.md` | 总结报告（人读入口） |

## 复现与校验

```bash
python -m kb_qa.eval --eval-set data/eval/eval.jsonl --ablation --judge \
    --k-list 5 3 10 --docs data/raw --out reports --notes "<备注>"
python tools/verify_evidence_chain.py reports/latest
```

脚本按文件名排序重算 `data/raw` 下 Markdown 语料的指纹，同时对照原始评测集和报告快照。历史 `latest` 以 Windows CRLF 字节计算，Git 检出可能转换成 LF。脚本先对照当前字节，再尝试仅转换换行以复核历史指纹。历史快照保存实际评测使用的六个字段，原始评测集另含 `note`，因此会校验原始文件指纹并逐条对照评测字段。新报告还对快照文件独立计算指纹。

- `passed` 表示可检查的证据都已通过且无待核验项。退出码为 0。
- `partial` 表示已检查项一致，还有索引或历史记录待核验。索引未随仓库分发时，输出 `index_status: unavailable`，退出码仍为 0。
- `failed` 表示存在指纹、样本或索引失配等问题。退出码 1。manifest 缺失或无法解析时退出码为 2。

可加 `--json` 查看结构化结果。对使用自定义输入的报告，用 `--raw`、`--eval-set` 和 `--chunks` 指定对应的语料、评测集和索引。索引检查核对文本块能否在源文档中定位，并在 manifest 有记录时比对篇数和块数。模型检查读取当时记录的名称、加载状态和维度。

## 数据来源与实测范围

- 83 篇文档中，`tools/gen_corpus.py --n 80 --seed 42` 可复现 80 篇模板生成的领域演示文档。其余三篇是项目已有的 `crop_ndvi.md`、`data_process.md` 和 `uav_mosaic.md`。
- 119 条评测样本包含 99 条可答和 20 条越界样本。问题及 gold 证据由脚本生成或配对。自动体检通过后，仍需人工复核 gold 块是否充分、问题是否有歧义、跨段证据是否齐全以及越界题能否从语料作答。
- `latest/` 的检索消融使用本机 BGE-M3 与 BGE Reranker。生成和评分使用 DeepSeek Chat，报告记录 99 次评委调用。离线 demo 使用哈希嵌入及脚本化替身验证链路。

> 历史 run 的 `embedding_model` 字段为 `unknown`（评测入口只读环境变量、建库参数没回写），
> 因此**无法自证**跑在什么模型上——这个问题已在 `model_info` 实测回写后修掉，
> 旧报告的问题与影响见 [`archive/README.md`](archive/README.md)。
