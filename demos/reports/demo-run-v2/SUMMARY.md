# 评测总结 · demo-run-v2

- 运行时间：**2026-10-24 16:18:43**
- 评测集：**16 条**（可答 15 / 不可答 1）
- 类型分布：`{'fact': 9, 'term': 6, 'out_of_scope': 1}`
- 评测集指纹：`45dd63e1edb24db2`（`demos\data\eval\demo_evalrun_eval.jsonl`）
- 嵌入模型：`fake-hash-64d`
- 建库配置：chunk_size=40, overlap=4, parent_size=150, 指纹=`3de8613c4254b5ee`
- 检索口径：top_k=5, recall_k=20

> 指标口径：MRR 为 **1-based** 排名倒数；Precision 分母固定为 k；幻觉率按忠实度 **严格小于** 阈值计。

## 一、检索消融（核心结果）

| 配置 | hit@5 | mrr@5 | recall@5 | precision@5 | ndcg@5 | n | P95 延迟(ms) |
|---|---|---|---|---|---|---|---|
| A_vector_only (向量) | 0.8000 | 0.6167 | 0.8000 | 0.1600 | 0.6636 | 15 | 0.1 |
| B_hybrid_rrf (向量+BM25) | 0.8667 | 0.7389 | 0.8667 | 0.1733 | 0.7708 | 15 | 0.3 |
| C_hybrid_rerank (向量+BM25+Rerank) | 0.8000 | 0.7556 | 0.8000 | 0.1600 | 0.7667 | 15 | 0.7 |
| D_hybrid_rerank_rules (向量+BM25+Rerank+规则) | 0.8000 | 0.7556 | 0.8000 | 0.1600 | 0.7667 | 15 | 0.6 |

## 三、分类型表现（哪个类型最弱）

**A_vector_only (向量)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 0.7778 | 0.6111 | 0.6548 |
| term | 6 | 0.8333 | 0.6250 | 0.6769 |

**B_hybrid_rrf (向量+BM25)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 0.8889 | 0.8148 | 0.8333 |
| term | 6 | 0.8333 | 0.6250 | 0.6769 |

**C_hybrid_rerank (向量+BM25+Rerank)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 0.8889 | 0.8889 | 0.8889 |
| term | 6 | 0.6667 | 0.5556 | 0.5833 |

**D_hybrid_rerank_rules (向量+BM25+Rerank+规则)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 0.8889 | 0.8889 | 0.8889 |
| term | 6 | 0.6667 | 0.5556 | 0.5833 |

## 四、失败样本（Badcase 回流清单）

**D_hybrid_rerank_rules (向量+BM25+Rerank+规则)**

共 3 条，下列前 3 条：

| qid | 类型 | query | gold | 实际召回 top5 |
|---|---|---|---|---|
| q03 | fact | 小目标召回率要求 | 01_检测技术要求.md#p0#c1 | 01_检测技术要求.md#p0#c2,01_检测技术要求.md#p0#c0,02_部署规范.md#p0#c0,01_检测技术要求.md#p1#c0,01_检测技术要求.md#p1#c1 |
| q06 | term | 影像分辨率要求 | 01_检测技术要求.md#p1#c0 | 01_检测技术要求.md#p1#c1,01_检测技术要求.md#p0#c0,02_部署规范.md#p0#c0,01_检测技术要求.md#p0#c2,01_检测技术要求.md#p0#c1 |
| q07 | term | 地面采样距离要求 | 01_检测技术要求.md#p1#c0 | 01_检测技术要求.md#p1#c1,01_检测技术要求.md#p0#c0,02_部署规范.md#p0#c0,01_检测技术要求.md#p0#c2,01_检测技术要求.md#p0#c1 |

## 五、评测集体检

✅ 未发现问题。

## 六、复现方式

```bash
# 本报告对应的完整参数见 eval_manifest.json
python -m kb_qa.eval --eval-set demos\data\eval\demo_evalrun_eval.jsonl \
    --ablation --judge --out reports
```
