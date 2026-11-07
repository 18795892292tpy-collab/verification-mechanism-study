# 来源核验机制研究（博士论文实验）

生成式 AI 辅助中小学行政决策时，"来源适用性核验"为什么有用：是因为检查了有区分力的证据，还是只是多算了一轮？

- 运行实验的完整说明（给人和 AI 代理）：[AGENTS.md](AGENTS.md)
- 实验代码与程序定义：[mechanism_study/README.md](mechanism_study/README.md)
- 已做实验的结果：[mechanism_study/report/dev_report.md](mechanism_study/report/dev_report.md)
- 案例编写与检查：[.claude/skills/verification-case-builder/SKILL.md](.claude/skills/verification-case-builder/SKILL.md)

API key 不在仓库里：复制 `mechanism_study/.env.example` 为 `mechanism_study/.env` 后填写。

## Codex v3 新题预试与额外固定草稿探索（2026-11-07）

V3 的 80 个 P0 均返回答案，但冻结规则将 CLI 的三类配置诊断全部判为技术失败，原门槛为 `technical_block`；原始失败状态及记录均保留。事后 A1 敏感性分析按精确诊断例外复核，80/80 行动选项符合规则答案，该口径是 **事后探索**，不等于原门槛通过。此后另立并冻结 128 次作者预设草稿挑战，127 次完成、1 次技术失败；失败最终行动虽符合答案，主要统计仍按计划分母计 0，未重抽。共实际 208 次 CLI 尝试。

四程序的错误草稿修复分别为 P1/P3/P7 16/16、P8 15/16；正确草稿未保留各 0/16。I78 为 +0.125，完全来自上述技术失败计入计划分母，不能据此声称 P7 优势。固定草稿修复是条件挑战能力，不是自然错误修复率；本批没有真人、独立领域专家审核或确认集。独立审计的完整性 PASS 只支持记录及计算可核查，整体 WARN / same-family / provisional。[V3 详细报告](experiments/codex_verification_v3/report/DEV_REPORT.md) · [最终独立审计](experiments/codex_verification_v3/audits/FINAL_EXPERIMENT_AUDIT.json) · [原始材料与归档验证](experiments/codex_verification_v3/)。

## Codex v2 固定 800 任务开发实验（2026-11-07）

已完成 800/800 个计划任务，实际 CLI 调用也是 800 次，无重试，800 条回答均可解析。8 个新家族（材料适用性、规则条件各 4 个）构成 80 题，每题 2 次重复；160 个共享 P0 首轮对应 640 个 P1/P3/P7/P8 复核。五程序的 **action 选项均为 160/160 正确**，证据在场的首轮错误为 0，修复率为 NA；这些数字不评价理由完整性或引用质量，也不证明方法等价、机制优势或核验无效。

- [完整中文报告](experiments/codex_verification_v2/report/DEV_REPORT.md)与[本仓库报告第 11 节](mechanism_study/report/dev_report.md#11-codex-v2-固定-800-任务开发批次2026-11-07)
- [评分汇总](experiments/codex_verification_v2/analysis/dev/summary.json)与[逐任务评分](experiments/codex_verification_v2/analysis/dev/scored_runs.csv)
- [执行前固定预算修订](experiments/codex_verification_v2/protocol/EXECUTION_AMENDMENT.md)、[冻结分析计划](experiments/codex_verification_v2/protocol/analysis_plan.json)与[执行中并发修订](experiments/codex_verification_v2/protocol/CONCURRENCY_AMENDMENT_2026-11-07.json)

执行前已规定即使出现天花板也完成固定矩阵，不另做模型筛查或校准、不按 P0 结果选题。667 个任务终态后按用户要求由 3 直接改为 12 并发，6 并发未实际运行；耗时汇总混合两个并发阶段，不能解释为因果提速。只使用同主机 Codex CLI 显式请求 `gpt-6-astra / ultra`，底层权重快照未知。本批是虚构学校规则的 `simulation_only` 开发研究；题库经过同模型家族内部匿名盲审，没有真人被试或独立教育行政专家核定，与 v1、历史 DeepSeek 数据分开。

## Codex 首批开发实验（2026-11-07）

按研究者的新指示，另行使用当前 Codex 环境完成 10 次校准和 200 次开发作答，完整归档于独立目录；未续跑或混合历史 DeepSeek 数据。

- [中文实验报告](experiments/codex_verification_v1/report/DEV_REPORT.md)
- [完整材料与复算说明](experiments/codex_verification_v1/README_中文.md)
- [离线回放页面](experiments/codex_verification_v1/viewer.html)（下载后用浏览器打开）
- [三组科研图](experiments/codex_verification_v1/figures/)与[最终审计](experiments/codex_verification_v1/audits/FINAL_REVIEW.md)
- [发布清单与历史快照恢复说明](experiments/codex_verification_v1/PUBLICATION_NOTES.md)

五种程序均为 40/40 选项正确；首轮无自然错误，纠错率为 NA，不能据此判断机制优势或方法等价。按预设门槛停止扩大这一矩阵，未运行保留集。
