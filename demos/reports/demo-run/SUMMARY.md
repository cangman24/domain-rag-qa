# 评测总结 · demo-run

- 运行时间：**2026-10-24 16:18:43**
- 评测集：**16 条**（可答 15 / 不可答 1）
- 类型分布：`{'fact': 9, 'term': 6, 'out_of_scope': 1}`
- 评测集指纹：`45dd63e1edb24db2`（`demos\data\eval\demo_evalrun_eval.jsonl`）
- 嵌入模型：`fake-hash-64d`
- 建库配置：chunk_size=64, overlap=8, parent_size=220, 指纹=`49b2638500d53adf`
- 检索口径：top_k=5, recall_k=20

> 指标口径：MRR 为 **1-based** 排名倒数；Precision 分母固定为 k；幻觉率按忠实度 **严格小于** 阈值计。

## 一、检索消融（核心结果）

| 配置 | hit@5 | mrr@5 | recall@5 | precision@5 | ndcg@5 | n | P95 延迟(ms) |
|---|---|---|---|---|---|---|---|
| A_vector_only (向量) | 0.9333 | 0.7556 | 0.9333 | 0.1867 | 0.8016 | 15 | 0.1 |
| B_hybrid_rrf (向量+BM25) | 1.0000 | 0.9667 | 1.0000 | 0.2000 | 0.9754 | 15 | 0.2 |
| C_hybrid_rerank (向量+BM25+Rerank) | 1.0000 | 1.0000 | 1.0000 | 0.2000 | 1.0000 | 15 | 1.1 |
| D_hybrid_rerank_rules (向量+BM25+Rerank+规则) | 1.0000 | 1.0000 | 1.0000 | 0.2000 | 1.0000 | 15 | 0.3 |

### 多 k 值对比

**k=3**

| 配置 | hit@3 | mrr@3 | recall@3 | precision@3 | ndcg@3 | n | P95 延迟(ms) |
|---|---|---|---|---|---|---|---|
| A_vector_only | 0.9333 | 0.7556 | 0.9333 | 0.3111 | 0.8016 | 15 | 0.1 |
| B_hybrid_rrf | 1.0000 | 0.9667 | 1.0000 | 0.3333 | 0.9754 | 15 | 0.2 |
| C_hybrid_rerank | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 15 | 0.8 |
| D_hybrid_rerank_rules | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 15 | 0.5 |

## 二、生成层评测（含 LLM-as-Judge）

| 指标 | 值 | 含义 |
|---|---|---|
| refusal_accuracy | 0.9375 | 拒答判定正确率（可答不拒答、不可答要拒答） |
| judged | 15.0 | 参与判分的样本数（0 = 未启用评委） |
| relevance_mean | 5.0 | 相关性均分（1-5） |
| accuracy_mean | 4.0 | 准确性均分（1-5） |
| completeness_mean | 3.3333 | 完整性均分（1-5） |
| groundedness_mean | 4.0 | 忠实度均分（1-5，专测幻觉） |
| hallucination_rate | 0.3333 | 幻觉率 = 忠实度 < 阈值 的占比 |

评委配置：prompt `v1`，调用 15 次，失败 0 次，解析失败 0 次。

> ⚠️ LLM-as-Judge 存在位置偏见与自我偏好，本表用于**回归筛选**（快速发现版本退化），关键结论仍需人工抽检。

## 三、分类型表现（哪个类型最弱）

**A_vector_only (向量)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 1.0000 | 0.7037 | 0.7804 |
| term | 6 | 0.8333 | 0.8333 | 0.8333 |

**B_hybrid_rrf (向量+BM25)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 1.0000 | 1.0000 | 1.0000 |
| term | 6 | 1.0000 | 0.9167 | 0.9385 |

**C_hybrid_rerank (向量+BM25+Rerank)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 1.0000 | 1.0000 | 1.0000 |
| term | 6 | 1.0000 | 1.0000 | 1.0000 |

**D_hybrid_rerank_rules (向量+BM25+Rerank+规则)**

| 问题类型 | n | hit@5 | mrr@5 | ndcg@5 |
|---|---|---|---|---|
| fact | 9 | 1.0000 | 1.0000 | 1.0000 |
| term | 6 | 1.0000 | 1.0000 | 1.0000 |

## 四、失败样本（Badcase 回流清单）

**D_hybrid_rerank_rules (向量+BM25+Rerank+规则)**

_本轮无完全失败样本（hit@k = 0）_

## 五、评测集体检

✅ 未发现问题。

## 六、复现方式

```bash
# 本报告对应的完整参数见 eval_manifest.json
python -m kb_qa.eval --eval-set demos\data\eval\demo_evalrun_eval.jsonl \
    --ablation --judge --out reports
```
