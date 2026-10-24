# reports/ —— 历次评测运行

每个 `run-<时间戳>-<哈希>/` 目录是一次完整评测的产物，包含：

| 文件 | 内容 |
|---|---|
| `eval_manifest.json` | **运行指纹**：run_id、时间、评测集 sha256、切分参数与配置指纹、检索口径、评委信息 |
| `eval_set.jsonl` | 本次运行使用的评测集快照（与 manifest 里的 sha256 对应） |
| `retrieval_A~D_*.md` | 四档消融的逐档报告（指标表 + 分类型统计 + Badcase 清单） |
| `SUMMARY.md` | 总结报告（人读入口） |

## 运行清单

| run | 时间 | 评测集 | 备注 |
|---|---|---|---|
| `run-20261016-090235-a9a44c` | 09:02 | 114 条 | 最早一次基线 |
| `run-20261016-090544-76791d` | 09:05 | 114 条 | |
| `run-20261016-094927-06bc01` | 09:49 | 114 条 | |
| `run-20261016-095120-e5e604` | 09:51 | 114 条 | |
| `run-20261016-100221-991c15` | 10:02 | **119 条（99 可答）** | **最新一次，README 指标表引用自此** |

复现任意一次：`python -m kb_qa.eval --eval-set data/eval/eval.jsonl --ablation --judge --out reports --notes "<备注>"`，随后用 `--show` / `--compare` 核对指标。

> 说明：各 run 的 `eval_manifest.json` 中 `embedding_model` 字段为 `unknown`——这是评测入口从环境变量读取模型名、而运行 shell 未设置该变量导致的记录缺失（代码修复见 P0 清单）。上述运行均在装有 BGE-M3 与 bge-reranker-v2-m3 的本机 GPU 环境执行，索引证据（`data/vectors/` 为 1024 维 L2 归一化向量）与延迟画像（向量路 P95 48.6ms，精排 +131ms）均可佐证。
