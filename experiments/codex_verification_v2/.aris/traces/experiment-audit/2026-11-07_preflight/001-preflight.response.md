# V2 执行前独立完整性预审（第一轮）

- 日期：2026-11-07；目标：`liekkas` 上 `/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2`。
- 审查者：新上下文 Codex 子代理 `/root/v2_preflight_audit`，未编写被审实现；**review_independence: same-family；acceptance_status: provisional**。本接口未显示精确后端型号，故不冒称已独立确认某个型号或跨家族审查。
- **结论：FAIL，三个冻结前必须修复项；当前不得把此轮报告当作通过。** 主代理已接受三项，要求先保存本轮、实现修复后复用本审阅上下文复核。尚未给出最终放行结论。
- 仅直接阅读协议/代码/测试及构造题来源说明；未联网、未调用被试模型、未读取真实实验结果、未修改冻结输入、未写case_review文件、未推GitHub。独立探针均在可销毁临时fixture运行，不是实验作答证据。

## 三项待修问题

### PF-01：缺失 usage 被记为已知零（major）

`harness/evaluate.py:201,208,217` 把“usage对象存在”当作“两个计数字段已知”，字段缺失用 `.get(...,0)` 填零。独立探针 `empty_usage` 返回 `{}` 后得到 `usage_missing_attempts=0` 和 input/output=0；`partial_usage` 仅有 input=17，output仍报告0。两者都通过完整性。这可能少报真实资源消耗，也违背未知不猜测的协议。

必须逐字段验证非bool非负整数；未知保持null/空，完整总计若存在未知则null，已知小计单独命名并报告每字段缺失次数。

### PF-02：未校验会话/turn生命周期，重复完成事件覆盖用量（major）

`harness/runner.py:184–207` 只对事件名字白名单检查，`classify_final`只检查布尔turn_completed；`harness/evaluate.py:210,224`仅检测重复的已有session ID。`missing_session`探针无thread.started仍被归类complete且完整性通过（unique_sessions=0）。`repeated_turn_completed`含两个完成事件，usage 17/9被最后2/1覆盖，仍通过。

成功响应必须有唯一非空session ID及单一合法turn生命周期；冲突/重复生命周期应显式记协议/完整性失败，禁止静默选择末次usage或重采样。正常无final技术失败仍可按既定有限恢复流程处理。原始事件必须保留。

### PF-03：计划外原始记录被完整性统计静默忽略（major）

`harness/evaluate.py:156`只遍历frozen计划，未盘点计划外记录。探针在临时fixture增加 `runs/dev/unplanned_group/P0/record.json` 后，`passed_integrity`仍为true、实际attempt计数仍仅为计划内1。`analysis/progress.py:9`却会统计这份记录，进度与正式审计口径还会分歧。

必须盘点runs/dev下task/attempt/record路径，拒绝或明确报告计划外原始证据，并防止其从实际调用计数中消失。已计划任务内attempt多余目录已有拒绝测试，但未覆盖这一级路径。

## 已检查并通过的证据

| 项目 | 证据与边界 |
|---|---|
| 确切目标与固定800矩阵 | 主机/绝对路径已确认；实际公开题80，键完全覆盖，8家族各10题，4材料+4规则家族；调度160组、五程序各160。runner.py:111–126。 |
| 首轮共享、无结果选择 | runner.py:382–407先要求全部160 P0 terminal，四复核共享同一raw_final；prompt及first哈希重建验证；没有correctness驱动的筛选/重试分支。parse_failure原文保留。 |
| 锁、源和运行身份 | integrity.py:73–130原子write-once和跨进程flock；runner.py:90–158固定源文件/参数/调度、主机/根目录/CLI/依赖哈希，运行后manifest pin。测试真实spawn子进程锁竞争。 |
| 技术暂停与恢复 | runner.py:170–182、303–356认证/配额/网络暂停；已开始调用完成保存；有final绝不再采样；无final最多2次。未封口中断拒绝自动重采样，需保留审查。 |
| GT来源 A | evaluate.py:152、196–204只读预设键；CASE_SPEC.md:37和build_cases.py:657–696显示作者事实oracle先于字母映射。不是基于被试回答回填的GT；语义有效性由另行匿名审查负责。 |
| 计分/归一化 B | evaluate.py:76–99、156–209保留800计划分母，missing/parse/technical failure=0；自然P0错误条件分母，分母0→null；无模型自身最大值归一化。 |
| 结果存在 C | 不适用：执行前不读取真实结果，不声称任何性能数字或800实测完成。 |
| 管线/死代码 D | evaluate.run实际调用summarize并写出家族/contrast/诊断；800模拟端到端与恢复不新增调用测试通过。legacy ledger不是当前V2主入口，未当作结果证据。 |
| 家族contrast | evaluate.py:33–61，I78=P7−P8的rule均值减material均值，家族内配对、类型内家族等权；I73、P3−P1及完整配对敏感性单独实现；测试方向及家族不等样本数。 |
| 范围 E / 分类 F | analysis_plan与修订明确 simulation_only、4家族/类型、描述性开发实验、无总体优越性/等效性或真实教育效果；无外部教育行政专家参与。天花板不能建立机制结论。 |

## 独立验证与审查限制

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`：**58 tests，0 failures，0 errors，9.769 s**。CLI调用均mock，真实被试调用0。完整输出：`001-unit-initial.log`。
- 独立 `adversarial_probe.py`：五个探针均复现上述三类问题，结果保存为 `002-probes-initial.json`。这些fixture仅产生模拟数据，不进入真实实验目录。
- 初始故障探针与本轮报告不得被后续通过报告替换抹除；修复后追加新一轮证据。JSON保存本轮已审文件SHA-256。
- runtime_identity显式记录请求gpt-6-astra/ultra和CLI，但隐藏权重快照、sampling seed、temperature未知。预审不能独立验证供应方实际隐藏权重，也没有进行联网后端调用。
- 当前结论只涵盖执行工具链。不是80题的语义盲审，不是教育专家验证，也不是结果后审计。技术测试通过不抵消本轮已复现的缺陷。
