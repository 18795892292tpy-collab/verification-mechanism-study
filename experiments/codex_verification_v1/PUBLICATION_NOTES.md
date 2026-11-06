# v1 发布去重说明

按 Issue #2 的发布审查，本次省略重复的 10 个 `audits/legacy_snapshot/` 文件和完整 ZIP。历史数据在原仓库固定提交 `cf8a5b64bb221882348c0091f401a0e1f4847d24` 的 `mechanism_study/results/` 中仍完整保留。逐文件字节相等及 SHA-256 已核对，清单见 `PUBLICATION_OMISSIONS.json`。首次完整本地归档与 SHA-256 保留，不重新写入 Git 历史。

冻结的 24 个输入/代码文件、210 次模型作答、原始事件、评分及审计记录均未修改。原冻结哈希仍为 `d24e2ecc0aafe67c566a0afcd0c88b3d44db8e00d28340beac858765154f2d64`。

`SOURCE_FILE_MANIFEST.csv` 是原完整归档清单，包含本次省略的文件；`FILE_MANIFEST.csv` 是此次实际发布清单（不列清单自身、缓存及本地运行锁）。历史审计中的绝对路径、会话 ID 和文件哈希按执行时的记录保存，属于原始可追溯元数据，不是凭证；本次没有重写原始实验记录做匿名化。

正常复算 v1 的结果无需恢复历史快照。在仓库完整 Git checkout 中，若需要重新分析旧快照，可运行：

```bash
python experiments/codex_verification_v1/restore_legacy_snapshot.py
```

该命令只从固定历史提交读取 10 个已验证文件并恢复本地快照，不调用模型或网络，不读取密钥，拒绝覆盖内容不一致的文件。历史审计脚本默认拒绝覆盖原审计报告；应将新审计写入独立目录。恢复的重复副本由 `.gitignore` 排除。
