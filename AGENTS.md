# AGENTS

- 在本仓库根目录验证改动，使用本仓库的 `.venv`。KB Agent Platform 有独立的同名 `core` 包。
- 检索、切分和评测通用逻辑在 `core/`，应用装配在 `kb_qa/`。保持离线测试可用，模型、网络和索引使用现有可注入接口。
- 回归运行 `python -m unittest discover -s tests` 和 `python demos/demo_ingest.py`。改动证据校验时，再运行 `python tools/verify_evidence_chain.py reports/latest`。
- 评测指标标注语料和模型来源。保留历史报告原始指标与指纹，新跑一轮时产出独立报告。API Key 和本地索引保存在忽略路径。
- 先提交 diff 和验证结果给用户审计。得到用户确认后再创建 Git 提交。
