# Codex 核验机制实验：首批交付

完成日期：2026-11-07（北京时间）。准备目录沿用2026-11-06开始日期。

已完成10次校准、200次开发作答：4个合成案例家族、40个共享首轮组、5种程序。
显式请求模型为gpt-6-astra、ultra；运行后端为本机Codex CLI 0.166.0，新临时会话逐次作答。
没有真人被试，没有DeepSeek新调用，也未将历史数据混入本批。

## 先看这些

- `report/DEV_REPORT.md`：中文实验报告，包含结果、解释、资源和下一步。
- `viewer.html`：离线回放40题及200份真实模型回答，不再次调用模型。
- `figures/`：3组SVG、PNG、PDF科研图。
- `analysis/dev/scored_runs.csv`、`summary.json`：全计划评分与汇总。
- `runs/`：不可改写的输入、原始回答、事件、usage和分支记录。
- `protocol/frozen.json`：在模型作答前冻结的输入与代码SHA-256。
- `audits/final_review.json`：独立脚本复算与最终审查。
- `audits/legacy_audit.md`：历史3目录的只读审计；不代表复算全部历史H04。

P0正确率：40/40。后续扩展门槛：STOP_DEVELOPMENT_EXPANSION。
修复率若为NA，表示没有自然首轮错误作为分母，不表示0%修复。
不同代理和题目变体不是独立人类参与者。内部盲审不是独立教育专家验证。

## 只读核验与重新生成

在此目录运行：
```bash
python harness/runner.py --verify
python -m unittest discover -s tests
python harness/evaluate.py dev
python analysis/plot_results.py
```

以上命令不会调用模型。模型实验入口是`harness/runner.py --phase ...`，请不要把它与离线核验混淆。
`requirements-runtime.txt`记录实际版本，包含发行版构建号，不是跨平台pip锁文件。
不要在同一冻结批次修改提示、答案、模型配置或重抽首轮；新研究须另立版本。

所有统计图均从保存的真实记录生成。技能来源见`report/FIGURE_PROVENANCE.md`。
`FILE_MANIFEST.csv`列出包内研究文件SHA-256。
