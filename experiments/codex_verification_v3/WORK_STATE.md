# V3 工作状态
用户已授权开始实验。主机liekkas，V2保持只读。当前准备V2依据质量审核、新80题P0、条件性128固定草稿复核。模型调用尚未开始。

## 已恢复执行
- 2026-11-07：题库、运行器、旧依据审查已准备。独立预审先发现5项问题，修复后独立复测PASS；首轮报告和修复证据均保留。
- 80 P0题、32条件草稿经匿名内部审核；4题文字修订单独复审通过；不代表外部专家验证。
- 冻结 SHA256 bef848323484f7490f2ac5bbaf1eb67ca55af45745f22f74352c15dac8139887；首次被试调用在冻结之后启动，exec session4831，命令 python -u harness/runner.py --phase p0 --workers 12，log execution_p0.log。
- P0 80终态、完整性通过后运行 python analysis/evaluate.py p0 --write-gate；仅有效gate FAIL执行独立128 authored challenge，PASS停止此批并提出独立家族验证方案；技术故障不可触发challenge。所有已封存final不重抽。
- 目标 original GitHub 18795892292tpy-collab/verification-mechanism-study；发布checkout /home/grf/Desktop/Codex_Verification_Experiment_2026-11-06/github_publish/verification-mechanism-study，branch codex/verification-v3-pilot-2026-11-07，切自origin/main。
- 实验完成后复用 v3_integrity_audit 完成独立复算；生成中文报告/图、打包源文件/哈希清单，原始记录保持字节一致，再提交、推送并核验原仓库。

## 结果与归档阶段
- 原P0运行80次均返回final，但冻结规则将三条CLI诊断归为失败，80 technical_failure；原gate为technical_block，不允许原挑战。原始记录和冻结规则未改。
- 独立事后A1精确诊断例外分析80/80行动正确，仅属posthoc探索，原严格结果未变。无自然错误可估计自然修复率。
- 独立冻结的额外作者草稿探索完成128次，127 complete、1 technical_or_protocol_failure（stderr型号列表刷新超时；final行动正确但严格分母计失败），没有重抽。各程序错误稿正确16/16、16/16、16/16、15/16；正确稿均保留16/16。I78=.125完全由唯一技术失败造成，不支持机制优势。
- 实际被试208次、无重抽；两阶段、事后修订、CLI诊断与资源数据分开。无真人/外部专家/独立保留集。
- 独立最终复算完整性PASS、总体WARN same-family/provisional；中文报告和科研图已生成并复核。现准备上传到用户指定GitHub原仓库，发布状态写本目录外v3_publication。
