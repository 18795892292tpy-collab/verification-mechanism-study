已完成准备，未出最终 PASS 或实验结论，也未等待批次完成。

- [独立审计脚本](/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2/audits/independent_final_audit.py)：标准库实现，不导入原 scorer/runner，不调用模型。覆盖冻结哈希、800 计划与终态、160 P0 逐字共享、原始尝试/session/工具事件、无答案重抽、全树记录、失败日志、未知 usage、逐条评分与家族等权 I78/I73、NA。
- [准备说明](/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2/audits/AUDIT_PREPARATION.md)：记录 same-family / provisional、无独立专家验证、n=4/type、simulation_only 和操作方式。
- [完整 trace](/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2/.aris/traces/experiment-audit/2026-11-07_final/001-preparation.response.md)。冻结输入检查和 80 题公开规则 oracle 准备检查通过；离线探针未写伪造实验结果。最终入口已确认拒绝未完成矩阵。

后续原环境 CLI：

```bash
python /home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2/audits/independent_final_audit.py --final --write
```

需全部 800 终态和 `analysis/dev/summary.json`、`scored_runs.csv`、`family_results.csv`、`integrity_audit.json` 已写完且保持稳定。成功复算才新建 `audits/INDEPENDENT_FINAL_AUDIT.json`，拒绝覆盖旧审计；错误或未完成时退出码 2，不生成成功报告。

归档复算使用 `--archive-root /绝对/归档路径 --final`；无需原 CLI，明确输出 `archive_evidence_only`，不会声称恢复原主机运行。`--prepare-check` 可单独验证准备输入。

本轮没有修改冻结输入、原始 records 或其他作者脚本。请在 800 任务结束后 followup 同一 reviewer 进行实际审计与最终人工复核。
