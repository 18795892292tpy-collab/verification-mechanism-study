# V3 独立工具链预审（round 1）

日期：2026-11-07；host=`liekkas`；canonical root=`/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3`。

**Overall verdict: FAIL。review_independence: same-family；acceptance_status: provisional。**

本轮直接阅读协议、harness、评分器、tests与测试记录，重新运行作者33个离线测试（全通过），另运行11项独立对抗probe（6通过、5不通过）。所有subject subprocess均为mock；真实模型调用0。canonical被试数据/冻结输入均未修改。此报告不是最终实验结果审计。

## 已复现问题

### F1 (high): 跨阶段未封存尝试未计入门槛完整性
另一phase只有attempt_started.json与response.json而没有record.json时，collect_phase跳过该任务；80个P0完成后仍得到passed_integrity=true、challenge_allowed=true，虽然inventory记录81个attempt目录。应全局验证所有phase已有attempt，早期challenge痕迹必须拒绝门槛。
证据：`analysis/evaluate.py:174`, `analysis/evaluate.py:188`, `analysis/evaluate.py:212`, `analysis/evaluate.py:218`, `analysis/evaluate.py:224`。Probe: `cross_phase_unsealed_attempt_blocks_gate`。

### F2 (high): 响应文件与最终事件冲突被计为完成
mock response.json为A而最后item.completed/agent_message为B，输出仍是complete/A。两份原始结果应有一致性约束；冲突须保留并判为协议/完整性失败，不得重抽。
证据：`harness/runner.py:280`, `harness/runner.py:331`, `harness/runner.py:339`。Probe: `output_vs_final_event_consistency`。

### F3 (medium): 错误item和成功turn并存仍计为完成
包含item.completed/type=error（fatal response transport failed）的记录，若returncode=0且turn.completed，则service_block早返回，classify_final忽略error_items，判complete。需明确错误事件政策并使含未解释错误记录不能满足无技术失败门槛。
证据：`harness/runner.py:244`, `harness/runner.py:246`, `harness/runner.py:279`, `harness/runner.py:345`。Probe: `error_item_success_classification`。

### F4 (high): 后序partial final不能阻止新抽样
只预放attempt_02/attempt_started.json和response.json，attempt_01不存在。response_task执行新的attempt_01并返回，实际mock调用1次，未先拒绝旧final。应在任何新调用前核对全部attempt目录连续性及partial/final，避免遗漏后序已有答案。
证据：`harness/runner.py:380`, `harness/runner.py:398`, `harness/runner.py:406`, `harness/runner.py:444`。Probe: `later_partial_final_blocks_any_new_attempt`。

### F5 (medium): 目录锁追随符号链接并覆盖其目标
临时目录中将.integrity.lock链接至sentinel文件，DirectoryLock成功进入并ftruncate目标。runner先获取锁后inventory，无法在写入前拒绝。应O_NOFOLLOW打开并确认regular file，确保全局锁路径不改变别的目标。
证据：`harness/integrity.py:111`, `harness/integrity.py:121`, `harness/runner.py:465`, `harness/runner.py:466`。Probe: `directory_lock_symlink_refused_without_mutation`。

## A–F完整性检查

| 检查 | 状态 | 结论 |
|---|---|---|
| gt_provenance | WARN | 计划明确作者预设虚构制度真值、simulation_only；本轮题库仍构建，实际真值与草稿关联尚未审完。 |
| score_normalization | PASS | 直接correct/计划分母；family对比先每族两draft平均再每类型四族平均。独立六个contrast/condition复算一致；不存在以模型输出max/mean归一化。 |
| result_existence | WARN | 预审时canonical根目录无frozen.json、raw record、attempt marker；没有被试结果可复算。此为预审，不支持任何结果或方法差异主张。 |
| dead_code | PASS | active runner只导入复用integrity.py的DirectoryLock与_write_once；其余legacy helper未用于V3评分，没有声称那些函数产出V3结果。评分、gate、usage函数均被实际mock路径或独立probe调用。 |
| scope | PASS | 计划把8家族列为开发材料，每类型仅4族，不作p值/确认性/真人/专家/留出验证主张。 |
| eval_type | simulation_only | 作者构造的封闭虚构制度，不是真实世界领域真值。 |

## 已通过部分与限制

冻结输入、运行参数、主机/路径/CLI身份、计划CSV、未知文件/符号链接inventory、正常目录锁竞争、已封存final恢复、解析失败不重抽、缺失usage、同一阶段session生命周期均有离线测试证据。CLI身份包含实际原生二进制，不只包装脚本。10个门槛边界和6个家族对比独立复算均符合预案；后两者不能抵消F1–F5。

截至本轮预审，canonical根目录没有frozen.json、raw record或attempt marker，case_review.json尚未提供。真实题库的规则唯一性、truth table、draft_condition与计划关联需要在构建完成后独立核对。没有任何自然错误率、修复率、差异或优越性结果可宣称。

## 复现与后续

- 完整probe脚本：`.aris/traces/experiment-audit/2026-11-07_v3_preflight/adversarial_probe.py`。
- 完整round1结果：`.aris/traces/experiment-audit/2026-11-07_v3_preflight/adversarial_results_round1.json`。
- 阅读文件副本与哈希：trace内`inspected_inputs_round1/`和`audited_input_hashes_round1.json`；这些仅为审计证据快照，目标始终为canonical根目录。
- 修复F1–F5后再审；后续仍须做题库关联核验、正式冻结核验及最终原始结果独立复算。
