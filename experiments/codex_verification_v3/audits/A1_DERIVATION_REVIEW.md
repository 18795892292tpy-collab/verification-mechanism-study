# A1事后派生脚本独立审计

**PASS（same-family / provisional）；限于A1派生分析，不授权任何模型调用。**

直接阅读`amendments/A1_posthoc/derive.py`、21项tests、README及全部派生结果。重新运行21项测试通过；另6项独立对抗检查通过，覆盖生命周期事件夹带tool、final后追加error、白名单对象额外字段、诊断/最终消息换位、空session及缺失usage。

从原始response/events及冻结key独立重算80题，确认诊断调整口径80 accepted、80 correct，八个family均10/10；每类型证据在场错误建议16题自然内容错误0，aligned正确16/16、missing正确8/8。Subject输入1,474,842、输出24,171，与派生summary、逐项rows及输出manifest一致。589个原始/冻结/原gate输入哈希在复查前后保持不变。

原严格口径始终80 technical_failure、0 complete、technical_block、challenge_allowed=false。A1的hypothetical threshold因自然错误不足为development_gate_failed；它明确标为NOT_A_RUN_GATE及automatic_execution_authorized=false，不是原门槛通过，也不直接授权C。

A1先确定诊断例外后的全部传输接受状态，再读取key评分；白名单匹配完整三条错误对象及顺序。没有删除错误、重抽final、覆盖原gate或写回原记录。使用量缺失不补零，分母保留80，family作为描述单位，无模型自产真值或自归一化。

本次未发现影响当前派生数值或原始完整性的漏洞。stderr政策是出现ERROR/FATAL字样拒绝，其余stderr保留并哈希；当前实际stderr只有已记录native-roots WARN，不能把该policy解释为已验证未来所有未知WARN。补充只读核验V2全部800份events.jsonl，800份均含相同三条诊断，README的历史计数相符。

被审脚本SHA256：`2cfa38ad66ec9d412b7b8346e326d3d5d05f7453d7a3bf0f450bb06efdbea245`。完整trace：`.aris/traces/experiment-audit/2026-11-07_v3_amendment/derive_independent_results.json`及`derive_author_tests_rerun.txt`。挑战执行器仍须另行复审通过。
