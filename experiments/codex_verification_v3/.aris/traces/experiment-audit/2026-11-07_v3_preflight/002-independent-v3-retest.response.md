# V3 独立工具链预审（round 2）

**结论：PASS；无已知工具链阻断。review_independence: same-family；acceptance_status: provisional。**

主机与canonical路径均已核对为 `liekkas`、`/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3`。这不是最终实验结果报告；真实模型调用0，原始及冻结输入未改。

## 复测证据

- 作者47项离线回归独立重跑全过（17.382秒）；当前源文件哈希与harness_tests.json一致。
- 原11项probe有10项有效，这10项修复后全部通过；8项新增probe全部通过。
- 新probe明确构造response=A、最后完成消息=B，判protocol_failure且恢复不重抽；更早的消息不会覆盖最后消息；空response与事件冲突也被拒绝。
- 晚序任务的partial attempt会在全批任何新调用前阻断；已封存challenge final缺record可零调用恢复；跨phase session重复被拒绝。
- 全部80个mock原始P0同时命中两类型4个自然错误/覆盖3族/12个aligned正确/6个missing正确的下界时，gate PASS；challenge被拒绝且调用0。另有10个门槛边界及6个family contrast复算通过。
- 实际80个P0和32个作者草稿通过独立stdlib脚本的唯一ID/key关联、完整factorial、四族/类型、public/draft哈希、草稿行动正误和来源字段检查。

## F1–F5处理

F1跨phase未封存记录漏检、F2最终来源冲突、F3错误item误判完成、F4后序partial允许新抽样、F5锁链接覆盖目标，均由新代码处理并通过有效离线探针。修复后读取代码、回归输出和探针结果见完整trace。

**审计更正：**原F2探针用字符串替换嵌套JSON，转义导致事件答案并未改变，因此round1“动态已证实”的表述不准确；原动态证据撤回。静态代码当时确实没有来源一致性判断。round2新增探针先明确验证实际response=A、event=B，再验证修复后失败状态与不重抽。原FAIL报告、原脚本和结果均保留，未提前覆盖或删除。

## A–F检查与范围

真值来源：simulation_only，作者预先制定虚构规则；实际语义真值/唯一答案仍须另行盲审，结构关联通过不替代语义审核。评分归一化：直接计划分母和每family等权，无自输出max/mean归一化。结果存在性：尚无真实被试结果可复算，不宣称自然错误率、修复率或方法差异。评分函数通过实际mock路径调用，legacy helper不被当作结果来源。范围明确为8个开发家族、每类型4族，无真人、外部专家或留出验证。

## 交付与后续

`audits/independent_recompute.py` 已准备，标准库实现，不导入被审runner/evaluate、不调用模型；直接核对frozen/raw/prompt/response/key、session、origin、planned分母、usage、P0门槛和challenge家族对比。5项纯函数自检通过，尚未执行最终数据审计。正式冻结后需复核对应hash；实验完成后才运行 `--execute-final`。

完整trace：`.aris/traces/experiment-audit/2026-11-07_v3_preflight/`。初轮意见保留为`round1_PREFLIGHT_REVIEW.md/json`；本轮原探针、补充探针和47项测试输出分别为`adversarial_results_round2.json`、`additional_results_round2.json`、`author_tests_rerun_round2.txt`。当前输入哈希见`audited_input_hashes_round2.json`。
