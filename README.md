# 来源核验机制研究（博士论文实验）

生成式 AI 辅助中小学行政决策时，"来源适用性核验"为什么有用：是因为检查了有区分力的证据，还是只是多算了一轮？

- 运行实验的完整说明（给人和 AI 代理）：[AGENTS.md](AGENTS.md)
- 实验代码与程序定义：[mechanism_study/README.md](mechanism_study/README.md)
- 已做实验的结果：[mechanism_study/report/dev_report.md](mechanism_study/report/dev_report.md)
- 案例编写与检查：[.claude/skills/verification-case-builder/SKILL.md](.claude/skills/verification-case-builder/SKILL.md)

API key 不在仓库里：复制 `mechanism_study/.env.example` 为 `mechanism_study/.env` 后填写。

## Codex 首批开发实验（2026-11-07）

按研究者的新指示，另行使用当前 Codex 环境完成 10 次校准和 200 次开发作答，完整归档于独立目录；未续跑或混合历史 DeepSeek 数据。

- [中文实验报告](experiments/codex_verification_v1/report/DEV_REPORT.md)
- [完整材料与复算说明](experiments/codex_verification_v1/README_中文.md)
- [离线回放页面](experiments/codex_verification_v1/viewer.html)（下载后用浏览器打开）
- [三组科研图](experiments/codex_verification_v1/figures/)与[最终审计](experiments/codex_verification_v1/audits/FINAL_REVIEW.md)
- [发布清单与历史快照恢复说明](experiments/codex_verification_v1/PUBLICATION_NOTES.md)

五种程序均为 40/40 选项正确；首轮无自然错误，纠错率为 NA，不能据此判断机制优势或方法等价。按预设门槛停止扩大这一矩阵，未运行保留集。
