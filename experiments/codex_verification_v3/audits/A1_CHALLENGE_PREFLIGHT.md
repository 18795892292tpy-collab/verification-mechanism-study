# 额外C探索执行器独立预审

**PASS；无已知阻断。same-family / provisional。**

被审最终driver SHA256：`9412da448003e6ff148b8c4c2a2873e9f961492347fe117c2a0d6c3bdb0d1fa8`。15项作者mock独立重跑全过；17项独立探针全过。审核期间真实模型调用0，原589个输入哈希未变，额外C尚未冻结或调用。

实际candidate授权、原strict gate、P0原始来源、A1派生summary/threshold/manifest/input hashes校验通过。128任务与原冻结challenge计划完全相同；128个prompt逐字对应原32份固定档案/草稿及P1/P3/P7/P8文本，未按P0表现筛选或改写。

已修复并复测授权仅信字段、生命周期夹带tool、跨P0/C session重复、来源metadata检查不足、未知顶层error、布尔返回码、response哈希覆盖缺失及runtime_empty链接问题。原有效final恢复不发新调用；晚序partial在全批派发前阻断；服务错误后停止新增派发并保存在途记录，失败记录恢复不重抽。目录锁与新运行目录隔离，原gate和raw只读。

本版明确每任务**最多1次attempt**、最多12并发；原协议上限2仅作来源说明，不实现自动重试。已有final或未封存attempt都不能静默补抽。未知诊断、stderr、事件形状、来源冲突、schema/返回状态异常均失败关闭。

原科学门槛仍是technical_block、challenge_allowed=false。新增阶段是另行登记的posthoc固定作者草稿探索，不能称原门槛通过或自然错误修复实验。A1派生分析独立审计已另行通过。

完整证据：`.aris/traces/experiment-audit/2026-11-07_v3_amendment/challenge_probe_round1.json`保留4项初次失败；`challenge_probe_round2.json`记录17项通过；两轮作者回归输出及对应源码快照同时保留。

## 由root执行的启动顺序

保持工作目录为canonical V3根目录。先把已核验candidate以exclusive create复制为authorization.json（若目标存在则拒绝覆盖），再依次执行以下命令。此审核不执行这些命令。

```bash
python -B amendments/A1_posthoc/challenge/driver.py --freeze
python -B amendments/A1_posthoc/challenge/driver.py --verify
python -B amendments/A1_posthoc/challenge/driver.py --run
```

复制的candidate、冻结manifest与driver哈希应保存至root执行记录。若verify或run拒绝，保持所有已有原始数据并独立诊断，不改原gate或重抽。
