# TASKS

| 状态 | 工作项 | 验收依据 |
| --- | --- | --- |
| 已验收 | 独立环境与离线入口 | 按 [README](README.md) 运行测试和主演示。入库、检索、回答引用与消融报告均可查看。 |
| 已验收 | 评测证据校验 | `python tools/verify_evidence_chain.py reports/latest`。历史语料和 119 条快照字段匹配，干净检出提示索引待核验。修改临时语料或样本会使校验失败。 |
| 已验收 | 简历展示入口 | [项目主页](README.md) 提供主演示，[历史真模型报告](reports/latest/SUMMARY.md) 提供指标与运行口径。 |
| 待验证 | GitHub Actions | 本地已复验 Windows 和 Linux。远端 CI 以推送后的实际运行记录为准。 |
| 待做 | 人工复核评测样本 | 抽检 gold 证据、问题歧义与越界标注，复核记录见 [评测说明](reports/README.md)。 |
