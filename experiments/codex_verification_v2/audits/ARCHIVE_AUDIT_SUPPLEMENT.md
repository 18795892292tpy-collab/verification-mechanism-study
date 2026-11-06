# 归档审计兼容性补充（原审计封存后）

原目标：`liekkas:/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2`。被核验归档：`/home/grf/Desktop/Codex_Verification_Experiment_2026-11-06/github_publish/verification-mechanism-study/experiments/codex_verification_v2`。

独立比较确认，runs 树唯一差异为进程锁 `runs/dev/.integrity.lock`：原目录7365条路径，归档7364条。该锁是调度状态，不是模型回答。原分析保留了原目录计数，旧审计器直接比较计数因而误报。此次修订不改变原始结果或总体 WARN / same-family / provisional 结论。

修订只允许显式 `--archive-root` 模式缺失这一精确路径。以原封存 `INDEPENDENT_FINAL_AUDIT.json` 的固定SHA-256约束历史清单：文件差集必须恰为该锁，其余5603个运行文件必须与历史字节哈希一致；原有未知路径及symlink检查保持生效。原目标模式仍使用原计数精确比较。stdout现在直接披露实际被审路径、归档模式、未恢复实验执行及7365→7364调节。

已用修订脚本分别只读复算原目标与上述指定归档，两者均完成且确定性完整性PASS；不是在G内替换脚本后复算。6项内存负向检查分别验证原目标缺锁、额外路径缺口、其他缺失、额外文件、字节差异及原审计未固定均被拒绝。静态子审阅未发现阻断问题；该子审阅未重跑完整审计。

归档命令（同步新脚本后）：

```bash
python /absolute/archive/codex_verification_v2/audits/independent_final_audit.py --archive-root /absolute/archive/codex_verification_v2 --final
```

无需原CLI或凭证；此命令只核验归档证据，不恢复原实验。不要使用 `--write` 覆盖原封存报告。

原脚本SHA-256：`e83d2a0c1d7328f4501f5c2552334ca564b5a0905746608ba94dcb8a7c89382d`。
修订脚本SHA-256：`958af4fe752d6f0583667de413fcd9ec34e77621eb789229742683d467751c20`。
原正式审计md/json、raw审计JSON、28冻结源及真实运行记录均未改。原正式审计中的脚本哈希仍表示当时审核版本，由本补充透明记录后续修订，不追改历史来源哈希。

详细命令输出、锁哈希、完整限定及负向检查见 `audits/ARCHIVE_AUDIT_SUPPLEMENT.json`；完整请求/响应见004补充trace。打包方需同步修订脚本与补充文件并重建清单。审阅者未修改G。
