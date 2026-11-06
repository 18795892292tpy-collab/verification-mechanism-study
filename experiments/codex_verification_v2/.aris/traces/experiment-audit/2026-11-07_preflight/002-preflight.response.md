# V2 执行前独立完整性预审（第二轮最终结论）

- 日期：2026-11-07；目标：`liekkas` 上 `/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2`。
- **结论：PASS，当前审查范围内没有未解决的冻结/运行完整性阻塞。可以按已授权固定800矩阵进行freeze/run。** 本审查者没有执行freeze或调用被试模型。
- **review_independence: same-family；acceptance_status: provisional。** 审阅者为原独立上下文 `/root/v2_preflight_audit`，非被审实现作者；第二轮有第一轮审查历史，不冒称另一轮全新独立审阅。精确后端型号未由本接口独立暴露；无跨家族或外部教育专家验证声称。
- 首轮FAIL完整保留于 `.aris/traces/experiment-audit/2026-11-07_preflight/001-preflight.response.md` 与同名JSON。第二轮中间发现和修复前复现也保留，未抹除失败证据。

## 缺陷闭环

| 编号 | 最终状态 | 独立核验结果 |
|---|---|---|
| PF-01 缺失usage记零 | 已修复 | evaluate.py:27–62逐字段只接受非bool非负整数；缺失总计null，已知小计及缺失attempt数单列。原empty_usage探针现在两类总计均null、missing=1；partial_usage为input=17、output=null、missing=1。 |
| PF-02 会话/turn证据漏验 | 已修复 | runner.py:184–220检查唯一非空thread ID及单一有序成功生命周期，重复完成不选末项usage。原missing_session与repeated_turn_completed探针均被协议/完整性拒绝；原始事件与完成usage列表保留。成功与无final技术失败明确区分。 |
| PF-03 计划外原始记录遗漏 | 已修复 | evaluate.py:65–108盘点完整runs树，拒绝计划外phase/group/procedure/attempt/raw文件及symlink；evaluate.py:239–247输出拒绝审计，actual_cli_attempts不伪装成完整计数。原unplanned_raw_record探针现在明确拒绝。 |
| PF-04 第二轮发现的恢复回归 | 已修复 | 初版修复将task最终raw_final错误用于较早attempt，导致合法网络失败→成功仍被审计拒绝。修复后evaluate.py:284–297逐attempt重建自身sealed final。补充独立探针证明paused_service→complete→评分通过，首个attempt字节不变，调用数1+1，随后恢复0调用，未知总usage保留null、已知小计10/5。 |

PF-04修复前证据在 `002-resume-regression.json`；最终证据在 `002-extended-final.json`。首轮五探针脚本未修改，直接用于第二轮复测。

## 当前验证证据

1. **独立重跑67项离线测试全部通过**：0 failures、0 errors、9.519秒；日志 `002-unit-final.log`。包含800模拟任务的端到端执行/评分、零新增调用恢复、跨进程锁、manifest/源码/CLI变化拒绝、有限技术重试、首轮共享、计划分母、家族等权对比。
2. **五个原始独立探针全部达到修复预期**：`002-probes-final.json`。两个usage探针保留未知；缺session、重复完成事件、计划外原始记录三个探针均明确拒绝。
3. **额外恢复端到端独立探针通过**：`002-extended-probe.py` / `002-extended-final.json`，验证保存旧attempt、合法恢复、评分、usage缺失及再次恢复无重复调用。
4. `audits/integrity_tests.json`记录67项通过；其9个源码/测试SHA-256均与当前文件吻合，独立结果见 `002-final-source-check.json`。没有只接受作者“通过”的口头结论。
5. 当前公开输入仍为80题、8家族，material/rule各40题即4家族；调度160组、每程序160，共800任务。没有增设筛查或按P0结果修改矩阵的代码。

## 其他关键检查

- **共享首轮与不重采样**：固定160个P0先完成；四复核只接收对应P0原文及哈希。错误答案、解析失败、有final的失败都不可再采样；未知工具/事件拒绝。没有按答对与否重新选择任务的分支。
- **身份与写入保护**：跨进程flock、原子write-once、运行manifest pin，源文件、调度、执行参数、主机、规范根路径及CLI/依赖哈希在恢复时验证。原始attempt与final不可被正常执行流程替换。
- **计分与contrast**：所有计划任务保留分母；非响应/解析/技术失败计0。修复率仅使用有完整P0响应的自然错误、零分母null。I78先家族内P7−P8配对均值，再类型内家族等权、rule减material；完整配对敏感性另报。无预测自身最大值归一化，不把变体/重复当独立家族。
- **GT来源与范围**：作者在作答前定义封闭虚构规则/事实oracle；评分读取预设键，非从被试输出倒推。评价类型为 `simulation_only`，4家族/类型的描述性开发实验。没有真实学校效果、总体优越性、等效性、确认性p值或隐藏权重已知的声称。天花板仍不能建立机制优势。
- **A–F审计分类**：GT来源PASS；归一化PASS；真实结果存在性本轮不适用；评分函数实际接入管线PASS；范围约束PASS；类型为simulation_only。第一轮这些已通过项的详细证据保留于001报告，本轮测试覆盖其未回归。

## 盲审来源链：只读核验，不是再次语义盲审

`002-case-provenance-check.json`记录：case_review的5个SHA、盲审答案的4个来源SHA均吻合；匿名包80个唯一ID映射后与最终public_text完全一致；最终答案对象逐项来自首轮70个未改题答案和10个修订题答案，未对审阅对象按key改写；80个动作与key一致、80个unique_answer=true。这里只确认文件来源、聚合与计数，不把已有审阅者的语义判断当作本预审者重新匿名作答，也不替代外部教育专家。

## 结论边界与证据保留

本轮真实被试调用0、联网0、freeze0；仅写本审计报告及trace，未修改题目、答案、协议、实现或case_review文件，未读取真实实验结果。测试和探针全部使用临时mock目录。未知供应方模型快照/采样种子/temperature与管理开销保持未知。此PASS只表示当前已审源码和输入哈希下没有发现未解决的预运行完整性问题，不能证明真实800次已执行，也不是结果后审计。

最终报告JSON记录所有本轮文件哈希。后续执行应保持这些已审输入稳定、保存原始失败与暂停记录；模型任务开始后的任何问题应按冻结规则原样报告，不能通过事后改题/改键改善结果。
