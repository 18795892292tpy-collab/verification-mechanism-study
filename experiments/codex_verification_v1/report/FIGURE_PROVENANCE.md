# 科研图表来源与生成记录

准备与完成日期：2026-11-07（Asia/Shanghai）。当前状态：**3 组科研图已由完整、通过审计的 200 个开发任务生成；9 个 SVG/PNG/PDF 文件已保存，逐张 PNG 视觉检查通过。没有生成占位结果。**

## 工具与技能

使用 `/home/grf/.codex/skills/kdense-matplotlib/SKILL.md` 中的面向对象 Figure/Axes、分类颜色、显式缺失值表达、300 dpi PNG 与 SVG/PDF 导出流程。本机检查到 Matplotlib `3.10.7+dfsg1`。

技能材料实质参与了脚本结构与输出规范；软件方法参考：

Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. https://doi.org/10.48550/arXiv.2609.00065

已于 2026-11-07 核对 [arXiv 记录](https://arxiv.org/abs/2609.00065)：作者与年份如上，当前页面显示 v2（2026-09-02 修订）。引用采用无版本后缀 DOI；页面没有列出期刊版本。

## 输入与门槛

脚本：`analysis/plot_results.py`。

仅读取真实开发实验分析产物 `analysis/dev/summary.json`、`analysis/dev/scored_runs.csv`、`analysis/dev/integrity_audit.json`。必须恰好 200 个计划任务全部完成、40 个分支组完整、4 个案例家族、5 个程序各 40 个回答，且完整性审计通过。绘图前还重新核对 CSV 与 summary 的正确数、修复/改错数、零分母 NA 及实际 token 合计。

输入缺失、部分完成、重复行、首轮哈希不一致或汇总不一致时拒绝渲染，不产生替代数据图。

## 图件及解释边界

1. `fig1_design`：40 个首轮，每个共享给四种独立复核流程，规则评分与家族分析结构。
2. `fig2_results`：五组最终正确率，以及四种复核的自然错误修复、正确答案改错。所有标签来自实际计数；零错误首轮时修复率显示“不可估计”，不画成 0%。不添加没有根据的置信区间。
3. `fig3_resources`：实际记录的 input/output tokens。P0 首轮只计一次；其他组仅展示相应复核任务的消耗，包含日志中的尝试。缺失 usage 为 NA，不推算 FLOPs、现金费用或人类工作负担。

全部图标注 “Synthetic computational pilot | 4 case families”。同一家族的题目变体不是独立人类参与者。

## 运行与审查

数据完整后先运行 `python analysis/plot_results.py --check-only`，再运行 `python analysis/plot_results.py`。输出为 3 组 SVG/PNG/PDF，300 dpi PNG，同时写 `figures/figure_manifest.json`，保存输入、脚本和每张图的 SHA-256。

渲染完成后，已使用 `view_image` 实际查看三张 PNG；标题、流程箭头、计数、坐标与脚注均未见裁切或重叠，无需版面修改。`figures/figure_manifest.json` 已更新为 `visual_review: passed`，并记录逐图审查和输入/输出 SHA-256 复核。

本绘图步骤没有调用模型，没有修改原始回答、冻结文件或评分。输入来自协调代理已完成的开发实验。五组均为 40/40 正确；证据在场的自然首轮错误为 0，因此修复率显示不可估计，四种复核的正确答案改错均为 0/32。资源图展示真实记录的各程序 input/output token 合计，未将这些计数解释成精确算力、现金费用或人类工作负担。
