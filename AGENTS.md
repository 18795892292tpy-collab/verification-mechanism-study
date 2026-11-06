# 给 AI 代理（GPT、Codex 等）的实验说明

本仓库是田培宇博士论文（教育行政，东南曼谷大学）中"来源核验机制研究"的实验代码、案例和数据。

研究问题：生成式 AI 给学校行政决策提建议，建议引用了真实材料，但材料的适用对象、时间版本或授权范围并不支持这个决定。这时，第二轮"来源适用性核验"之所以有用，是因为它检查了能区分不同行动的证据，还是只是因为多算了一轮？

## 2026-11-07：Codex v2 固定 800 任务批次

研究者授权“收尾准备题库并且启动800次 做完后提交到GITHUB”，本批材料单独放在 [`experiments/codex_verification_v2/`](experiments/codex_verification_v2/)。先读其 `protocol/EXECUTION_AMENDMENT.md`、`protocol/analysis_plan.json`、`protocol/CONCURRENCY_AMENDMENT_2026-11-07.json` 和 `report/DEV_REPORT.md`。执行前固定预算修订优先于旧提案中的额外筛查和追加预算建议，也不沿用 v1 的天花板停止门槛。

- 固定 8 个新家族（材料适用性、规则条件各 4 个），5 状态 × 2 建议，共 80 题；每题 2 次独立首轮重复，P0/P1/P3/P7/P8 共 800 个计划任务。160 个 P0 同时用于难度诊断和共享首轮，之后完成 640 个复核；不另外做模型筛查或校准，不按 P0 结果筛选、替换或删改家族，即使天花板也完成矩阵。
- 同主机 Codex CLI 0.166.0 显式请求 `gpt-6-astra / ultra`，底层权重快照未知。每次作答用新临时上下文；同组四种复核共享精确 P0 原文及哈希。不续跑 DeepSeek，不合并 v1 或历史 DeepSeek 数据。
- 已完成 800/800 个任务、800 次实际调用，无重试，全部可解析；五程序 action 选项均 160/160。证据在场的首轮自然错误为 0，修复率 NA，复核改错各 0/128。评分只评价 action，不证明理由完整、引用正确、程序等价或机制成立。
- 已有 667 个任务终态后，由 3 直接提高到 12 并发（6 未实际运行）。这是用户授权的执行中操作修订；科学输入、模型、提示、评分代码、重试上限及已有 final 未改。耗时和资源汇总混合两个并发阶段，不据此推断因果提速。
- 题库是虚构规则，已做同模型家族内部匿名盲审，未做独立教育行政专家验证。评价类型为 `simulation_only`，没有真人校长/教师被试。以案例家族为分析单位，每类型仅 4 个家族，只作开发性描述，不作确认性优越性、等价性或现实学校成效主张。
- 保留冻结输入、原始回答和失败记录。不得为追求差异而改答案或重采样；新的研究须另立版本。主要正确率使用计划分母，无响应/解析失败计 0，完整配对敏感性另报。计划任务与实际调用分开计数；无可核验计费时费用为 NA，未知编题/内部审查/管理开销不混入被试任务 usage。

以下旧 DeepSeek 环境、P0 筛查、续跑命令只适用于 `mechanism_study/` 历史条件，不是恢复 v2 或新发模型调用的指令。

## 2026-11-07：Codex 首批独立开发实验（v1）

研究者已另行明确要求使用当前 Codex 环境，并批准执行。本批完整材料在 [`experiments/codex_verification_v1/`](experiments/codex_verification_v1/)，先读其中文 README、执行修订、冻结分析计划和实验报告。以下“只用 DeepSeek flash”及续跑命令描述原 `mechanism_study/` 条件，不用于重写或混合这个新批次。

本批已完成 10 次校准、200 次开发作答；5 种程序均为 40/40，首轮无自然错误，纠错率 NA。预设扩展门槛未达到，已停止扩展。不要修改冻结输入或原始回答，不要为追求差异而重新采样；新实验须另立版本。原有 DeepSeek 运行没有继续执行。

## 先读这些

1. `mechanism_study/report/dev_report.md`：已做实验的全部结果（第 1–11 节），每节按 原目标—方法—结果—解释—下一步 写。
2. `mechanism_study/README.md`：程序 P0–P6 的定义和运行方法。
3. `mechanism_study/analysis/analysis_plan.md`：预先规定的分析（C1、C2、C3、NI1、NI2）。
4. `.claude/skills/verification-case-builder/SKILL.md` 及其 `references/`：如何编写和检查案例家族（尤其 `hard_tier.md`）。

## 环境

```bash
cd mechanism_study
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 填入 DeepSeek API key
```

Python 3.12。下面所有命令都在 `mechanism_study/` 下运行。`.env` 不在仓库里：不要提交它，不要打印或记录 key。`harness/keep_awake.py` 只能在 Windows 上用，其他系统不需要。

## 研究者定下的规则（不要自行改变）

- **只用 DeepSeek flash。** API 模型名 `deepseek-flash` 就是 DeepSeek-V4.1-Flash（2026-11-06 价格页标明版本为 DeepSeek-V4.1-Flash-1017）。不用本地模型，不换其他模型。分析计划里"3 个模型"的旧设计已由研究者改为只用 flash。
  - **例外：** 2026-11-07 研究者授权在 Codex 环境中用 `gpt-6-astra / ultra` 做独立开发批次 `experiments/codex_verification_v1/` 和固定 800 任务批次 `experiments/codex_verification_v2/`。各批单独存放、单独报告，彼此及与 DeepSeek flash 数据均不合并，也不作为 flash 结论的依据；v2 的执行范围以上文及其冻结协议为准。
- **两种条件，分文件夹存放、分开报告，绝不合并：**
  - 不推理（第 1–3 轮的全部数据）：`.env` 里 `LLM_MODEL=deepseek-chat`。服务器返回 deepseek-flash，不产生推理 token。温度 0.7，`--max-tokens 4000`（默认值）。
  - 推理（当前条件）：命令里加 `--model deepseek-flash --max-tokens 32000 --timeout 400`。推理强度用默认的 high。推理模式下温度参数被忽略。不要用 4,000 的上限：此前的推理探测中 P3 复核 80 次有 77 次被截断，结果无效。
- **比较不同程序时一律加 `--branching`。** 这样每个"题目 × 重复"只调用一次首轮，P0 就是这个答案，P1–P6 都复核同一个首轮答案。不加时，首轮的随机波动会制造虚假的程序差异（第 6 节）。
- **以案例家族为分析单位。** 按回答计算的符号检验忽略家族内的相关，只作参考。
- **新家族先做 P0 难度筛查**（`--procedures P0 --repeats 2`，再运行 `screen_report.py`），再跑全套程序。
- **开发家族是探索性的。** `cases/dev`（F01–F08）和 `cases/dev_hard`（H01–H12）还没有经过独立专家审核，F03、F05、F08、H11 的答案尚有争议。确认集必须先用 `freeze_cases.py` 冻结，再用 `--confirm-manifest` 运行。`cases/*_KEY.md` 是盲审答案，不要发给审核专家。
- **报告前检查** parse_ok、截断（finish_reason = length）和推理 token。打分器遇到推理 token 会警告；推理条件下出现这个警告是正常的，截断警告则不正常。
- **报告写进 `report/dev_report.md` 的新一节**，用中文，按 原目标—方法—结果—解释—下一步，并在"主张—证据表"里加行。分析方法要在看结果之前写下（参见第 9 节的"预先规定"）。

## 当前状态（2026-11-06）

| 结果文件夹 | 条件 | 状态 |
|---|---|---|
| 第 1–3 轮各文件夹（`screen_*`、`dev_*`、`probe_thinking_*` 等） | 见报告 | 已完成并写入报告 |
| `results/flash_branch_dev` | 不推理，P0–P6 分支，2 次重复 | 160 组完成 31 组后暂停（研究者改为推理条件） |
| `results/flash_think_branch_dev` | 推理，P0–P6 分支，2 次重复 | 研究者手动停止；2026-11-07 去重审计：160 组完成 49 个唯一组（52 个分支，其中 3 个重复）；原记录无错误、无截断 |
| `results/flash_think_branch_hard` | 推理，P0–P6 分支，2 次重复 | 研究者手动停止：240 组完成 39 组，无错误，无截断 |
| `results/screen_local_qwen7b_*` | 本地 Qwen2.5-7B | 已停用，只作旁证存档，不进入结论 |

两个推理运行都可以用下面的同一条命令续跑：已完成的组会跳过。续跑前先确认研究者同意并查余额（停止时余额 5.24 元，跑完两个文件夹还需约 34 元）。每次只在一台机器上续跑同一个文件夹，跑完立即提交并推送，避免两份互相冲突的数据。

## 命令

运行（推理条件；先加 `--limit 3` 试跑 3 组）：

```bash
python harness/runner.py --cases cases/dev --out results/flash_think_branch_dev --procedures P0,P1,P2,P3,P4,P5,P6 --repeats 2 --branching --model deepseek-flash --max-tokens 32000 --timeout 400 --concurrency 8
python harness/runner.py --cases cases/dev_hard --out results/flash_think_branch_hard --procedures P0,P1,P2,P3,P4,P5,P6 --repeats 2 --branching --model deepseek-flash --max-tokens 32000 --timeout 400 --concurrency 8
```

中断或报错后，重跑同一条命令即可续跑；有未完成记录的组会整组重跑，所以各程序始终复核同一个首轮答案。

打分与分析：

```bash
python harness/scorer.py results/flash_think_branch_dev --cases cases/dev
python harness/scorer.py results/flash_think_branch_hard --cases cases/dev_hard
python analysis/branch_report.py results/flash_think_branch_dev/scored_runs.csv --cases cases/dev
python analysis/branch_pooled.py --run results/flash_think_branch_dev/scored_runs.csv cases/dev --run results/flash_think_branch_hard/scored_runs.csv cases/dev_hard --out results/flash_think_branch_pooled
python analysis/analyze.py results/flash_think_branch_pooled/combined_P0_P4.csv --out results/flash_think_branch_pooled/analysis
```

`branch_pooled.py` 给出 20 个家族合并后的修复率、损坏率和家族配对比较（含 P5、P6）；`analyze.py` 给出分析计划中预先规定的 C1、C2、C3、NI1、NI2（只含 P0–P4）。

## 费用

DeepSeek flash 价格（元/百万 token，空闲/高峰）：输入缓存命中 0.02/0.04，未命中 1/2，输出 4/8。高峰是工作日北京时间 9:00–12:00 和 14:00–18:00，其余时间和周末为空闲价。

实测（空闲价）：不推理每次调用约 0.004–0.005 元；推理条件下开发集约 0.014 元、难案例集约 0.017 元，P0–P6 全套 2,800 次约 44 元。推理复核的输出长度：P0 约 1,300–1,500 token，P3 约 5,000–5,700 token，最长约 10,500 token。

跑长任务前先查余额：`GET {LLM_BASE_URL}/user/balance`（带 Authorization 头，不要打印 key）。余额不足时调用会失败并记为错误，充值后重跑同一命令即可。
