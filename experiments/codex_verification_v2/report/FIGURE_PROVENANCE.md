# v2 图表、报告与数据来源

此文件说明展示方法和来源追溯。脚本准备阶段作 Python 源码编译和内存中资源接口 fixture 检查，未把 fixture 写入实验目录。800 个真实终态记录与评分审计齐备后，已运行正式绘图和报告生成；这些展示脚本没有调用被试模型。正式图表的逐张视觉审查证据见 `figures/visual_review.json`，通过状态以 `figure_manifest.json` 中的 `visual_review` 为准。

## 生成前置条件

唯一执行目标为 `liekkas:/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2`。`analysis/plot_results.py` 与 `analysis/write_report.py` 均要求真实 `analysis/dev/summary.json`、`scored_runs.csv`、`integrity_audit.json` 和 `protocol/frozen.json` 已存在，全部 800 个冻结计划任务已有封存终态记录。

成功、解析失败、技术失败、协议失败、首轮失败导致未启动复核都属于可报告终态；运行中、暂停、未执行和缺记录不是可报告终态。通过门槛不要求 800 次成功：失败如实保留并按计划分母计 0。脚本不会调用模型、重试任务或产生 mock 结果。

脚本调用已有评分器的只读验证函数，核验冻结源文件、记录身份、原始事件/回答哈希、首轮共享文本、attempt 元数据、CSV 与原始记录一致性；使用只读 `evaluate.inventory_runs()` 检查整个运行树，拒绝未计划文件、额外 attempt 和符号链接，并核对记录/attempt/started/sealed 数量；检查 `lifecycle_errors` 及每个 attempt 自己的事件与 final，再复算 family / procedure / interaction 汇总。异常记录或未通过完整性审计时拒绝产图。仅离线测试成功不代表真实实验完成。

资源字段遵循冻结评分器契约：CSV 含 `sum_input_tokens`、`sum_output_tokens`、`known_input_tokens`、`known_output_tokens`、输入/输出各自缺失 attempt 数、任一字段缺失 attempt 数，以及 `input_tokens/output_tokens`。未知总计在 JSON 是 null、CSV 是空串；已知小计不会替代未知总计。输入输出分别判定，仅非负整数 token 有效，bool/float/字符串/非字典 usage 均不强转。无 attempt 任务的资源总计、小计与缺失次数为 0，但 task 的 input/output 别名为空串，不计作 usage 完整任务。展示器独立从原始 attempts 重建每行，再核对 summary 和每个程序的资源契约。

无 final 的技术失败可能缺少完整生命周期；如果合法重试后来成功，前一次失败不会因为后一次 final 被误判为返回答案的生命周期错误。只有该 attempt 自身声明 turn_completed 或自身已有 final 时，生命周期缺陷才触发该项审计拒绝。

## 执行中并发修订

本批在用户第二次要求提速后，667 个任务已终态并封存时安全停止原 3 并发调度器，剩余 133 个计划任务改用上限 12 并发；6 并发未实际运行。依据 `protocol/CONCURRENCY_AMENDMENT_2026-11-07.json` 与 `harness/run_concurrency_override.py`，这是执行中操作性修订，与固定 800 的执行前科学方案修订分开披露。此处的 667/133 是切换快照与剩余计划数，不是剩余任务已经成功完成的声明。

正式生成时，展示器仅只读核验修订及 driver 哈希、667 个既有记录的哈希、`audits/concurrency_amendment_applied.json`、`audits/concurrency_invocations/*.json` 和 `runs/dev/progress.jsonl`。原 28 个冻结源文件仍用原校验器核查；不导入或调用并发覆盖驱动。应用证据与启动日志须显示直接 3→12，发现 6 或其他配置则拒绝用这一披露出图。并发配置是上限，不表示全过程持续达到该并发度。

报告单列执行中偏离，资源图说明两种并发阶段混合；追加证据与 driver 一并进入输入 SHA-256 清单，输出 manifest 保存派生并发摘要。切换前后并非随机性能对照，任务组成、运行时段、服务端负载、排队和暂停可能不同，不能推断因果提速倍数、单次推理速度或成本同比下降，也不能据混合阶段累计时长比较各程序速度。源码编译本身不表示 800 项已完成；正式结果仅在全部真实终态和评分审计通过后生成。

## 四组图

- `fig1_design.{svg,png,pdf}`：固定设计，标题明确标为 **Planned design**。8 家族（4 material + 4 rule）、80 题 × 2 重复，160 个 P0 加 640 个复核。底部单独列实际成功、失败/阻断和 attempt 数，避免将计划数量冒充完成数量。
- `fig2_family_accuracy.{svg,png,pdf}`：8 家族 × 5 程序，在全部题目与证据在场/错误建议层分别显示正确数/计划数和比例。失败留在分母，状态变体和重复不作为独立家族。
- `fig3_family_contrasts.{svg,png,pdf}`：present_flawed 的主要 I78（P7−P8）及次要 I73（P7−P3）。点为各家族配对差，菱形为类型内等权均值，线为观测家族最小值至最大值。线不是置信区间；交互值是 rule 均值减 material 均值。
- `fig4_resources.{svg,png,pdf}`：各程序实际 attempts 的输入/输出 token 与时长合计。未知不置零；不完整 usage 只画已知小计并加斜线与星号，标出可知/实际 attempt 数。没有任何可知值则 NA。累计 attempt 时长不等于墙钟时间；图脚披露 3→12 执行中并发变化、667/133 切换范围与性能推断限制。账单费用 NA，管理开销未知并排除。

所有图使用 Matplotlib 面向对象接口；白背景、色盲较友好的 cividis / 定性色、文字计数与纹理辅助编码，SVG/PDF 矢量输出和 300 dpi PNG。图中文字使用英文以避免依赖未确认安装的中文字体；中文解释见报告。脚本不导入、拼接或复述 v1 结果。

## 报告和哈希清单

`report/DEV_REPORT.md` 仅在相同门槛满足后生成，区分计划数、终态数、成功数、失败数、阻断数和实际 attempt 数。条件纠错无自然首轮错误时为 NA；同时说明未成功 P0 不能当作自然错误。报告列主要、次要、完整配对敏感性、难度诊断与实际资源。

固定 800 相对原 Issue 3 额外筛查与扩展建议的执行前偏离依据 `protocol/EXECUTION_AMENDMENT.md` 明示；不会将难度阈值改作事后筛选或停止规则。无真人、无外部专家、同模型家族审查局限及描述性推断边界必须保留。

图生成时写 `figures/figure_manifest.json`，报告生成时写 `report/report_manifest.json`：包含生成时间、任务数、实际 attempts、冻结源文件、评分 CSV/JSON、全部任务原始文件、生成脚本及本文件的 SHA-256，并记录输出文件哈希。生成前后检查源哈希不变。清单只在真实结果生成时产生，不预填哈希或结果。每次重新渲染将图清单视觉审查状态重置为 `pending`；只有实际通过 `view_image` 检查最终 PNG、核对数据与输出哈希后，才写 `passed` 和视觉审查证据哈希。渲染成功不能冒充视觉验收。

## 运行顺序

在 800 个终态及真实评分产物齐备后，在上述唯一目录执行：

```bash
python3 analysis/plot_results.py --check-only
python3 analysis/plot_results.py
python3 analysis/write_report.py
```

`--check-only` 仍要求真实完整输入，不支持 toy/mock 或部分实验渲染。准备阶段仅执行源码编译与内存中的资源字段/CSV fixture 检查；这些接口检查不能替代正式生成时对 800 项真实数据的完整核验。

## 技能来源

本次采用 `/home/grf/.codex/skills/kdense-matplotlib/SKILL.md` 的 Matplotlib 面向对象接口、多格式导出与可访问配色建议。作者提供的参考条目：Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents.* arXiv:2609.00065. <https://doi.org/10.48550/arXiv.2609.00065>。依本任务禁止联网的要求，未在线核实此参考条目的元数据或最新版本；它是方法工具来源说明，不是实验结果证据。
