# 执行中并发修订独立审核

**结论：PASS，可按已授权修订启动后续12并发；本次审查未发现阻断项。** 这是同一独立审阅上下文的后续审核，`review_independence: same-family`、`acceptance_status: provisional`。不构成外部专家验证。

目标为主机 `liekkas` 的 `/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2`。本审查没有启动真实实验、没有改动冻结文件或真实records；真实被试调用0。仅读取源码、修订和哈希，对测试使用临时mock目录。

## 检查结果

- **原冻结保证仍有效**：独立调用原 `runner.verify()`通过。原 `runner.MAX_WORKERS`及 `execution_config.max_workers`仍为3。baseline frozen SHA-256为 `f5f73d297f3cc6b3f4049770dc6688a2ddc72ca66a784a89fd712d9c243afaf1`。`clone_run`仅在私有函数globals里将MAX_WORKERS改为12；verify、response_task、gate和所有被调用函数仍为原函数及原globals（driver:21–25）。
- **实际并发12**：driver:87将workers=12传入原run函数体，原 `ThreadPoolExecutor(max_workers=workers)`及调度上限据此运行。独立模拟通过12方barrier测得同时活跃mock调用峰值12，不仅核对配置数字。
- **667→800恢复不重抽**：独立建立160个P0加507个复核的667份已完成mock记录后启动driver，只新增133个mock调用，最终800任务/800独立session、评分完整性通过；原667份record的SHA无一变化；再恢复一次新增调用0。首轮继续使用原response_task和原始P0哈希约束。
- **互斥锁**：driver:72在校验及应用修订时获取与原runner相同的DirectoryLock，原run函数体再次获取同一运行锁后才调度。独立竞争锁探针确认拒绝进入。两次锁获取间允许其他合法调用先行，但实际dispatch仍由原run锁互斥，随后按已有记录恢复，未发现重复派发路径。
- **修订与账本**：driver:28–65验证baseline/driver哈希及3→12参数，拒绝计划外原始工件。首用必须完整盘点当前terminal记录；667份既有record哈希在canonical目标上独立核验通过。应用后seal_json固定整份修订和哈希，之后修改修订会被拒绝，独立探针确认。
- **留痕**：应用证据及每次调用独立记录位于非冻结audits目录，progress同时记录actual_workers=12；原baseline没有伪改为12。此次修订明确为执行中3→12；6并发没有作为已运行阶段记录。修订明确并发阶段混合，不能据此直接推断因果提速。

## 修订身份与验证证据

- driver SHA-256：`15adc3074c13d6322c1e1373701488502335a9fc9745a3a022ed3d61fb12d41c`。
- amendment SHA-256：`db685add1b3f1467816e4c5e72d58bab66e92d938678a624204918ac1cfd448c`。
- 作者提供的5项测试由本审查者重新执行：全部通过，2.043秒。保留日志 `001-independent-test-rerun.log`，未以作者结论代替执行。
- 额外独立精确规模恢复探针：`concurrency_probe.py`及 `002-independent-667-resume.json`；覆盖峰值12、只补133、原667不变、再恢复0调用、锁拒绝、applied修订防替换、原冻结哈希不变和最终评分。
- canonical只读校验快照：`003-canonical-amendment-check.json`。

全部证据保存在 `.aris/traces/experiment-audit/2026-11-07_concurrency/`。本PASS限定于上述已核验代码和修订哈希，不声称后续133个真实任务已经完成；最终报告仍须标注执行中的并发变更与实际资源用量。
