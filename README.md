# domain-rag-qa · 垂直领域 RAG 知识问答系统

> 面向**领域文档分散、术语密集、编号型号多**的场景：答案必须可溯源、检索必须可度量、调参必须可回归。
> 混合检索（BM25 + 向量 + RRF 融合 + 交叉编码精排）、父子块双层索引、低置信拒答、引用溯源、逐层消融评测。
>
> **561 项单测零第三方依赖可跑**（CI 单个测试 job 约 7 秒，含 checkout）；评测报告带运行指纹与评测集哈希，**可复现**。

![CI](https://github.com/cangman24/domain-rag-qa/actions/workflows/ci.yml/badge.svg) ![python](https://img.shields.io/badge/python-%3E%3D3.10-blue) ![tests](https://img.shields.io/badge/tests-561%20passing-brightgreen) ![deps](https://img.shields.io/badge/test%20deps-0-brightgreen) ![license](https://img.shields.io/badge/license-MIT-blue)

---

## 快速开始（5 分钟，无需 GPU / API Key / 任何第三方包）

```bash
python -m unittest discover -s tests   # 561 项单测，纯标准库零依赖（12 项因可选依赖跳过）
python demos/demo_ingest.py            # 全流程：文件 → 父子块切分 → 双索引 → 混合检索 → Agent → 评测
python demos/demo_agent2.py            # 六个 Agent 场景（脚本化决策，无需 API Key）
```

其余离线 demo：`demos/demo_core.py`（切分与 RRF 融合）、`demos/demo_pipeline.py`（检索链路与指标）、`demos/demo_eval.py`（检索层消融）、`demos/demo_evalrun.py`（一条命令产出可复现报告）、`demos/demo_service.py`（服务层 + CLI + SSE）。`make demo` 一键冒烟全部 6 个。

## 解决什么问题

| # | 问题 | 方案 |
|---|---|---|
| 1 | 文档格式与层级复杂，**固定切分导致语义断裂**，召回噪声大 | 递归切分 + 标题层级保留 + **父子块双层索引**（子块检索保精准，父块生成保上下文完整） |
| 2 | 纯向量检索对**专有名词、编号、型号**命中率低 | **BM25 + 向量双路召回**，RRF 融合；编号/型号走规则召回 |
| 3 | 长文档超出上下文窗口，**模型产生幻觉且答案无法追溯** | **低置信拒答** + Prompt 强制**引用原文片段**，引用只在确定作答后推送 |
| 4 | 检索调参依赖人工，**缺少可量化、可回归的评测手段** | 自建评测集（119 条）+ **逐层消融实验** + 分类型统计 + Badcase 回流 + 运行指纹 |

## 核心指标

**真实语料消融**（83 篇领域文档 / 303 个块，评测集 119 条 / 99 条可答，本机 BGE-M3 嵌入 + bge-reranker-v2-m3 精排，RTX 3080 Ti；报告与运行指纹见 [`reports/latest/`](reports/latest/)）：

| 配置 | Hit@5 | MRR@5 | NDCG@5 | P95 延迟 |
|---|---|---|---|---|
| A 纯向量 | 0.6061 | 0.4524 | 0.4660 | 51.1 ms |
| B + BM25 / RRF | 0.6667 | 0.4843 | 0.5049 | 70.1 ms |
| C + Reranker 精排 | **0.6970** | **0.5827** | **0.5874** | 211.7 ms |
| D + 编号规则召回 | 0.6970 | 0.5827 | 0.5874 | 189.5 ms |

**生成层**（LLM-as-Judge，99 条可答样本）：拒答正确率 **89.1%**、忠实度 **4.67 / 5**、幻觉率 **1.01%**。

> **D 档与 C 档五个指标完全相同** —— 规则召回在这 99 条上**零增益**，收益不能算到它头上；
> 规则层保留是因为它服务于检索之外的场景，但在本评测集上就是没有贡献，如实记录。
> 调参历史（Hit@5 0.35 → 0.70 的 5 次运行）在 [`reports/archive/`](reports/archive/)；
> 旧报告无法自证语料与模型（详见该目录 README），数字一律以 `reports/latest/` 为准。

**数字可自证**：`python tools/verify_evidence_chain.py reports/latest` ——
校验索引语料与磁盘是否逐字一致、manifest 是否写明模型名、向量维度是否实测（1024）。
manifest 里的 `model_info` 与 `corpus_fingerprint` 由运行时实测写入，不是手抄常量。

**同一套消融框架可离线复现**（哈希假嵌入，4 篇文档 / 18 条评测，用于验证框架本身能否拆开各模块贡献，`python demos/demo_ingest.py`）：Hit@5 0.875 → 1.0，MRR 0.62 → 0.93。

## 系统架构

```
                    ┌─────────────────────────────────────────┐
   文档 ──────────►  │ loaders    多格式解析 md/txt/json/docx/pdf │
                    └────────────────────┬────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │ recursive_chunk  递归切分 + 标题层级       │
                    │   ├── 父块（parent_size，喂模型，上下文完整）│
                    │   └── 子块（chunk_size，检索用，召回精准）  │
                    └────────────────────┬────────────────────┘
              ┌──────────────────────────┴──────────────────────────┐
              ▼                                                     ▼
   ┌─────────────────────┐                             ┌─────────────────────┐
   │ InMemory/Chroma 向量库│                             │   BM25Index（自实现） │
   └──────────┬──────────┘                             └──────────┬──────────┘
              │  top-20                                           │  top-20
              └───────────────────────┬───────────────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │  RRF 融合（免调参、抗量纲）  │
                        └─────────────┬─────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │ Reranker 交叉编码精排 top-5 │
                        └─────────────┬─────────────┘
                                      ▼
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   ┌─────────────────────┐                       ┌─────────────────────┐
   │ 低置信拒答（阈值可扫） │                       │ 父块回吐 + 引用溯源   │
   └──────────┬──────────┘                       └──────────┬──────────┘
              └───────────────────────┬───────────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │  LLM 生成（强制引用 [1][2]） │
                        └─────────────┬─────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │ CLI / FastAPI / SSE 输出   │
                        └───────────────────────────┘
```

## 仓库结构

```
core/                18 个共享模块（16 个纯标准库）：检索 / 评测 / LLM 客户端 / 服务层
kb_qa/               应用装配层：CLI / FastAPI / uvicorn 入口 / 评测命令 / 生产装配
tests/               561 项零依赖单测（含工程配置一致性守护）
demos/               6 个离线 demo（demos/live/ 预留真机冒烟）
tools/               语料与评测集生成器（固定 seed，可复现）
data/raw/            83 篇语料 · data/eval/ 评测集（gold 标注）
reports/             历次评测运行（运行指纹 + 消融表 + Badcase），见 reports/README.md
```

## 接真模型（可选，需要 GPU + DeepSeek Key）

```bash
conda create -n agent_rag --clone fieldai -y
conda run -n agent_rag pip install "transformers==4.44.2" --force-reinstall --no-deps
conda run -n agent_rag pip install -e ".[ml,serve]"
export HF_ENDPOINT=https://hf-mirror.com        # bge-m3 与 bge-reranker-v2-m3 各约 2.2GB → models/

# 建库 → 问答 → 一条命令出可复现评测报告
conda run -n agent_rag python -m kb_qa.cli ingest --docs data/raw
conda run -n agent_rag python -m kb_qa.eval --eval-set data/eval/eval.jsonl --ablation --judge --k-list 5 3 10 --out reports
```

> `transformers` 必须锁 4.44.x：sentence-transformers / FlagEmbedding 尚不兼容 5.x（conda 克隆环境常自带 5.19.0，不降级会在加载模型时直接报错）。

HTTP 服务：`pip install -e ".[serve]"` 后 `uvicorn kb_qa.server:app --port 8000`（或 `make serve`）。接口：`/health`、`/chat`、`/chat/stream`（SSE）、`/debug/retrieve`、`/debug/service`。

## 为什么这些逻辑能离线验证

向量库、LLM 调用、Embedding、Reranker、Checkpointer 全部是**可注入接口**：用内存实现 + 假 transport 就能覆盖重试、退避、限流、缓存、拒答、熔断——环境问题（chromadb 装不上、API 限流、GPU 没就绪）不阻塞业务逻辑验证，真模型接上后代码一行不改。这条边界由 CI 守护：测试环境**故意不装** torch / chromadb / fastapi（见 `.github/workflows/ci.yml`）。

## 设计决策精选

完整版见 [`kb_qa/README.md`](kb_qa/README.md)，面试高频四条：

1. **RRF 为什么优于加权求和**：BM25 分数范围 `[0, +∞)`，向量相似度 `[-1, 1]`，量纲不可比；RRF 只用排名 `1/(k+rank)`，天然免疫量纲且几乎免调参。
2. **父子块为什么用嵌套切分而非位置反查**：文本可能重复、overlap 会让边界模糊，位置反查是脆弱启发式；嵌套切分后归属关系结构性确定，子块永不跨章节。
3. **中文 BM25 的单字噪声与 `min_score`**：单字 + bigram 切分下，无关查询也能凭高频单字拿到正分（实测噪声分 1.09 vs 相关查询 6~8）；阈值按「拒答正确率 vs 漏答率」在评测集上扫出，不拍脑袋。
4. **拒答判定为什么必须匹配固定话术**：用户问"精度要求是多少"、模型答"精度要求为 0.90"——只搜"未找到"会误伤；匹配完整话术「知识库中未找到」且限前 60 字符，两者兼顾。

## 已知局限（如实声明）

- 评测集 gold 标注由生成脚本自动定位，**大规模人工复核未完成**（存在循环论证风险，已在 reports 集体检中标注）
- 尚未做多租户隔离与增量更新（新文档入库需重建索引）
- Dockerfile / docker-compose.yml 已编写并通过配置一致性测试，但未在本机构建过镜像
- 未接入 RAGAs 等第三方评估框架（有意为之：自实现更可控且便于讲解）

## License

MIT，见 [LICENSE](LICENSE)。
