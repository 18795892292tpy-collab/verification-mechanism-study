# V3 严格口径原始审计与额外C阶段评估

**原始来源完整性通过；原冻结科学门槛仍为 technical_block。** 审核为same-family/provisional；没有新增模型调用。

对canonical `liekkas:/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3` 全量只读复核：80条终态记录、80个已封存attempt、80个独立session，每题一次；80个returncode=0、最终response与事件逐字一致、schema有效。冻结文件、prompt、marker、meta、原始event/response及record哈希均相符。当前没有未封存尝试、未知或顶层错误、工具事件、跨阶段尝试；583个审计输入文件哈希已记录。冻结SHA为`bef848323484f7490f2ac5bbaf1eb67ca55af45745f22f74352c15dac8139887`。

冻结政策明确“any error item prohibits complete; no documented recoverable-error exceptions”。因此0 complete、80 technical_failure是该政策的正确执行，独立严格门槛复算为technical_block、challenge_allowed=false。失败计入计划分母得到的0/80不是80个内容决定错误；本诊断未按key评分已有final的内容正确性。

## 实际诊断分类

1. 80次`skip_host_skill_discovery` under-development warning：原文明称warning，属启用配置提示；不能凭此断言隐藏行为绝对无影响。
2. 80次code-mode host disabled/fail-closed：与故意禁用工具的配置相符，没有实际工具调用事件。
3. 80次skills context budget：原文报告全部skill descriptions已移除、另144个未纳入。属于模型可见上下文准备诊断，不能证明隐藏上下文完全等同于理想空白环境。
4. stderr每次仅一个native root certificates WARN（error_count=2），共80次；实际请求均完成。没有观察到网络或认证失败，但这不构成对任意证书错误的通用豁免。

前三条在80次中的对象和顺序完全相同；抽查5份V2历史原始日志也逐字相同。它们足以支持“已有配置诊断导致过于保守的失败分类”的解释；不应把所有type=error普遍视为无害。

Subject使用量完整：input 1,474,842，output 24,171；管理、编题和审核开销未知，货币账单未核验。

先前预审没有把已有历史CLI配置诊断纳入mock测试，这是预审覆盖不足。冻结后改变错误政策属于明确的执行规则修正，不能隐去这一偏离。

## 能否追加C

可以作为**明确偏离原门槛的额外探索阶段**，因为32份草稿及全部128个程序组合已在P0前固定，且无需按本批答案或程序优劣挑选材料。这不让原门槛变成通过。

启动前应以追加、不可覆盖的amendment固定新规则及全部128任务，记录理由、时间、原frozen/draft/key/hash、精确三条诊断例外、模型与CLI身份、预算和调度。使用独立输出目录、独立“额外探索授权”记录；原decision_gate不得伪造通过，原冻结、raw、meta和record不得修改。全部已返final绝不重抽；未来未知错误、工具事件、原始冲突、生命周期/返回码/schema失败仍拒绝。每个结果保留严格状态及诊断调整后的派生状态。

C必须执行全部预写草稿和四程序，不按P0内容、早期C结果或期望差异改样本；保持12并发上限及仅无final时最多2次技术尝试，保留失败计划分母和家族等权。新非冻结执行代码需独立复审后才调用模型。

该设计能描述固定作者草稿的条件修复/保持能力。事后诊断例外和偏离门槛必须披露，不能声称原预登记C有效触发、自然错误率或自然纠错净收益，也不支持优越性、等价性、真人或留出验证。错误规则对80题一视同仁且有历史诊断证据降低结果选择风险，但不消除事后更正属性。

## 证据

完整trace：`.aris/traces/experiment-audit/2026-11-07_v3_diagnostics/`，含`strict_recomputed.json`、`source_hash_manifest.json`与`raw_examples.json`。本报告不修改原始实验，不创造任何原gate。非冻结A1脚本仍待独立复核。
