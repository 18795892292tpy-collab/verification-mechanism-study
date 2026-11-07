# A1：原始 P0 的事后派生敏感性分析

此目录不属于原冻结输入。分析标记为 `posthoc_exploratory`。原来 80 条
`technical_failure`、原运行、原冻结代码和原门槛全部保留；这里不会创建或覆盖
`analysis/decision_gate.json`，也不会调用模型或重抽任何回答。

原 CLI 把三条配置诊断发为 `item.completed/type=error`。它们分别提示实验功能、
禁用 Code Mode 和移除技能描述；前两条在 `turn.started` 之前，第三条在它之后。
原冻结规则规定任何 error item 都不能 complete，因此原口径仍是 `technical_block`。
这些诊断在 V2 800 次调用中也以相同原文出现，但这不使事后修改成为预注册分析。

`derive.py` 独立读取原文件，不导入 runner/evaluate。它按完整对象逐项比对三个诊断，
还限定原事件顺序、单一会话和 final、退出状态、双 final 字节一致性与冻结 JSON schema。
额外、缺失、变体或未知错误均不获豁免；工具/生命周期/哈希异常直接拒绝分析。
所有 stderr 都保留和校验哈希，ERROR/FATAL 诊断仍拒绝；已有 native-roots
证书载入 WARN 不被改写，也不被当作三条 error-item 白名单之一。

脚本核验全部冻结文件及 CLI 包/原生二进制、主机与路径、完整 80 次目录、计划、
提示、record/meta/start marker、原始事件、使用量与唯一 session。先确定全部运输
有效性，再对照冻结答案逐项计分。失败保留在计划分母内；缺失 usage 不补零。
写出前后比较全部原文件哈希，并以只读共享锁排除正在运行的原 dispatcher。

运行方式：

```bash
python -B amendments/A1_posthoc/derive.py
python -B -m unittest discover -s amendments/A1_posthoc/tests -v
python -B amendments/A1_posthoc/derive.py --write-results
```

最后一条命令只创建本目录的 `results/`，若已经存在则拒绝覆盖。
`threshold_diagnostic.json` 具有 `NOT_A_RUN_GATE=true`，不具备启动权限。
输出同时保留原失败口径和派生口径；原失败口径的零正确计数不能解释成模型 80 个
实体决策都错了。每类型只有四个构造家族，仅作描述，无 p 值、真人或留出验证结论。

## 额外挑战的技术与方法边界

即使派生口径下自然错误不足，原严格门槛仍不允许启动原 challenge。
原 runner 正确拒绝这种状态；不得删错误记录、改状态、替换原 gate 或猴子补丁绕过它。

若决定继续做 128 次预设草稿挑战，应另写前瞻的探索性扩展 C：

1. 在新 manifest 中绑定原冻结哈希、32 份预设 draft 和 128 项计划哈希；注明
   因诊断分类偏差追加探索，原研究门槛未通过，不能声称按原 gate 自动进入。
2. 在新调用前冻结并独立审核扩展的代码、错误白名单、派生指标、预算和执行规则。
   沿用原模型、CLI、flags、提示、四程序及并发，不能更换模型环境来补救既有答案。
3. 全部新 raw/manifest/进度/派生状态写到扩展自己的目录，独立全局锁；将原 P0
   目录列为只读输入。不得复用任何原 P0 final 做自然错误修复实验。
4. 原有 final、未封存尝试、完整 attempt 目录及幂等续跑先全局核查；任何已有 final
   不重抽，技术重试只在无 final 且上限允许时发生，未知错误继续拒绝。
5. 只报告作者预设错误的修复率及作者预设正确的损坏率，不能与自然 P0 混合。
   原始严格研究、A1 敏感性分析、扩展 C 分开列清楚计划/实际调用与协议偏差。

本 A1 未实现扩展 C 的调度器，也没有启动任何挑战任务。
