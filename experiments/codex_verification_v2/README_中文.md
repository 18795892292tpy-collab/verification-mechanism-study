# Codex 核验机制 v2：固定 800 任务开发实验

8 个合成案例家族（4 材料适用性、4 条款条件），80 题、每题 2 次首轮重复、5 种程序。全部 800 个计划任务已有终态；其中成功完成 800，实际 CLI 尝试 800。请求模型 gpt-6-astra / ultra；没有真人被试、没有 DeepSeek 新调用。

- [中文报告](report/DEV_REPORT.md)：结果、解释、失败与资源范围。
- [离线回放](viewer.html)：80 题 × 2 次重复，各含共享首轮及4种复核。
- [科研图](figures/)：设计、家族正确率、对比与实际任务资源（SVG/PNG/PDF）。
- [评分数据](analysis/dev/)：[原始记录](runs/dev/)；不修改或重新抽取已有回答。
- [执行前修订](protocol/EXECUTION_AMENDMENT.md)：固定800，160首轮只是描述性诊断，没有另外筛查或结果驱动选题。
- [执行中并发修订](protocol/CONCURRENCY_AMENDMENT_2026-11-07.json)：用户授权在667次完成后，将剩余133次从3并发提高至12；6并发未运行。原冻结输入和既有答案保持原样；时间资源统计混合两个并发阶段，不能用于因果性提速比较。
- [题库规范](cases/CASE_SPEC.md)、[内部盲审](audits/case_review.json)、[工具链预审](audits/PREFLIGHT_REVIEW.md)。
- [独立最终复算](audits/INDEPENDENT_FINAL_AUDIT.json)：内部同模型家族审查，非外部教育专家验证。

P0 正确率 160/160。纠错率分母为零时为 NA，不是零效果；天花板不能证明方法等价或机制优势。重复调用、题目变体与建议方向不是独立人类或独立家族。每类仅4个构造家族，结果仅是 simulation_only 开发性描述。

## 归档复算（不调用模型）

在明确下载的完整归档目录中可运行：

```bash
python audits/independent_final_audit.py --archive-root /绝对/归档路径 --final
```

独立复算脚本仅用 Python 标准库，核对归档的内容哈希、原始记录和统计，不需要原 CLI。它只证明这份归档证据的一致性，不声称在原电脑重新运行了实验。

原主机、原绝对路径以及原 CLI 二进制完全匹配时，可运行 `python harness/runner.py --verify` 和 `python harness/evaluate.py dev`。runner/evaluator 的严格身份检查故意拒绝把副本或不同环境当成原任务恢复；不要修改 frozen.json 来绕过检查。模型执行入口是 `--phase dev`，不要与只读复算混淆。

冻结SHA-256：`f5f73d297f3cc6b3f4049770dc6688a2ddc72ca66a784a89fd712d9c243afaf1`。`FILE_MANIFEST.csv` 为本次归档文件清单；排除缓存、空运行目录、临时文件和进程锁。本地 ZIP 位于本目录上一级，GitHub只提交解包研究文件，避免重复存储。

原始日志保留执行时路径、会话ID和原始字节。这里的计量仅涵盖被试任务，作者、内部审阅及协调开销完整用量未知；费用为NA。没有独立教育专家、真实学校参与者、保留集或跨模型确认。
