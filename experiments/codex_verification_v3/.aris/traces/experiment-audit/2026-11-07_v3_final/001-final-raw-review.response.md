# V3 最终独立实验审计

**总评：WARN；原始来源完整性PASS。审核独立性same-family，接受状态provisional。**

审计直接读取原P0、严格gate、A1派生及额外C的冻结/授权/提示/事件/响应/真值，不导入被审runner、derive或driver计算结果。目标主机为liekkas，canonical根目录为`/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3`。没有新增模型调用，没有修改冻结文件或原始记录。

## 三种口径必须分开

| 阶段 | 计划/实际attempts | 完成与主要结果 | 解释 |
|---|---:|---|---|
| 原严格P0 | 80 / 80 | 0 complete，80 technical_failure；原gate保持technical_block | 三条CLI配置诊断触发原冻结“任何error item拒绝”政策；这不意味着80个内容决定错误。 |
| A1事后诊断派生 | 使用同80份final，新增0 | 80/80内容正确，每族10/10；两类型自然错误均0 | 精确诊断例外是事后规则更正，假设阈值未满足，不是原gate通过。 |
| 额外C探索 | 128 / 128 | 127 complete，1 technical_or_protocol_failure | 使用P0前固定的32份作者草稿及四程序，单独授权冻结；明确偏离原门槛。 |

A1两类型证据在场错误建议各16题，错误0；正确建议各16/16；缺失条件各8/8。因此本批无法支持自然错误方法比较。不得把A1或额外C说成原研究按预先门槛合法触发的结果。

## 额外C按计划分母复算

| 程序 | 错误草稿修复 | 修复率 | 正确草稿损坏 | 总体主口径正确 |
|---|---:|---:|---:|---:|
| P1 | 16/16 | 100% | 0/16 | 32/32 |
| P3 | 16/16 | 100% | 0/16 | 32/32 |
| P7 | 16/16 | 100% | 0/16 | 32/32 |
| P8 | 15/16 | 93.75% | 0/16 | 31/32 |

每family/程序/草稿正误条件的分母为2；每类型4个family等权。错误草稿P7−P8：材料0，条款0.125；因此I78=0.125（12.5个百分点）。仅R05的family差为0.5，其他family均0。I73及P3−P1为0，正确草稿保持对比均0。

**I78的非零值完全来自一项技术失败，不是内容修复能力差异，不支持P7优越性。** 所有127项按执行规则完成的final行动均正确；另一个失败项也保存了正确行动，但必须在主口径保留失败0。128/128可见final行动匹配key只能作为原始内容诊断，不能取代127/128主口径，也不能据天花板宣称程序等效。

## 唯一失败的完整证据

任务：`R05_decisive_change_draft_error_r1/P8`。record的`problem`为`unrecognized stderr`。进程returncode=0；七个事件按顺序完成；response与最终消息逐字相同，行动B与key相符。stderr除已知native-roots WARN外，还包含：

`ERROR codex_models_manager::manager: failed to refresh available models: request timed out`

新冻结执行器仅允许指定stderr格式，因此本项正确保留`technical_or_protocol_failure`，没有重新抽样或放宽规则。该错误反映CLI模型目录刷新超时；不能笼统声称其内容回答失败，也不能因为内容正确就改成complete。

证据文件：

- `amendments/A1_posthoc/challenge/runs/R05_decisive_change_draft_error_r1/P8/record.json`
- 同目录`attempt_01/events.jsonl`、`response.json`、`stderr.txt`。

该record的classification将session/usage清为空；本审计从原始事件恢复资源统计与会话身份，未修改record。该次input=18,622、output=606，均已纳入下表。

## 来源、使用量与执行核验

1368个原始、冻结和派生来源哈希通过读取前后比较。原80项和额外128项每项恰一attempt，总208次、208个不同session，无跨阶段复用、无已有final重抽。按起止记录复算两阶段峰值均12。128个C提示逐字绑定原32草稿及P1/P3/P7/P8，作者origin明确，原strict gate字节未改。

| Subject资源 | Input tokens | Output tokens |
|---|---:|---:|
| 原P0 80次 | 1,474,842 | 24,171 |
| 额外C 128次（含失败） | 2,380,276 | 69,329 |
| 合计208次 | 3,855,118 | 93,500 |

没有usage缺失。Input已包含其缓存部分，不能再把cached tokens重复相加。编题、管理、审核等开销未知；未核验账单，货币费用为NA。

## A–F完整性结论

- **A 真值来源：PASS。** 作者在被试回答前固定虚构制度与keys，非模型输出自生真值；预试前匿名解题及4题修订绑定已留档。
- **B 评分归一化：PASS。** 计划分母保留失败，家族等权；没有按模型自身max/mean归一化。
- **C 结果存在与数值：PASS。** 所有208个subject final/attempt均有对应原始文件；此报告数值由原始事件、响应和key独立复算。
- **D 实际执行：PASS。** 结果均由已存在记录支持；没有phantom调用、重抽或未执行方法成绩。
- **E 范围：WARN。** 仅8个开发家族、每类型4族、一次回答；事后诊断分类及额外C偏离原门槛，不能作确认性、优越性或等价性结论。
- **F 评价类型：simulation_only。** 无真人、外部专家或新留出家族验证；同模型家族审查不提供外部效度。

后续若要比较自然纠错，应使用新的结构不同家族并预先验证执行器事件模型；本批不应追加到出现有利差异为止。

## 产物与可复核路径

机器结果：`audits/FINAL_EXPERIMENT_AUDIT.json`。独立脚本：`audits/independent_final_v3.py`，使用审计者自己的`audits/independent_recompute.py`辅助函数，不导入被审实现。

主要JSON字段：`original_p0_strict`、`A1_p0_posthoc`、`extra_C`、`extra_C_failures`、`combined_subject_usage`、`p0_rows`、`extra_C_rows`及`source_hashes`。`extra_C.procedures[程序].error`是错误草稿修复子表，`.correct`是正确草稿保持/损坏子表，不是总体正确整数。

原冻结SHA：`bef848323484f7490f2ac5bbaf1eb67ca55af45745f22f74352c15dac8139887`。额外C冻结SHA：`9c688ee45310e3211a0766adffefb7a9c28f7b765786fd60c974200678beb635`。报告图正在生成，实际图文仍待另行视觉及数值审阅。
