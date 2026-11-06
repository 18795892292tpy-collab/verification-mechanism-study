# 活跃执行状态

目标：完成新题库与固定 800 次实验，审计后提交原 GitHub 仓库。
主机 liekkas；本目录为 V2 唯一规范源。
当前阶段：800/800任务与评分已完成；最终审计、出图、回放验收后归档，准备发布GitHub。下文保留执行过程的时间顺序记录，以末尾状态为准。
计划：160 P0 + 全部 640 复核，无结果驱动筛选。
代理：v2_cases_build 写 cases/prompts/keys；v2_harness 写 harness/tests/analysis；legacy_task1_fix 在现有 G checkout 修旧代码。
G=/home/grf/Desktop/Codex_Verification_Experiment_2026-11-06/github_publish/verification-mechanism-study
原仓库=https://github.com/18795892292tpy-collab/verification-mechanism-study
不要重跑或修改已产生 final 的任务，不运行 DeepSeek，不删除 Fork。

## 追加状态
- v1 发布清理本地提交 77cca53，冻结24文件验证+32tests通过。GitHub push TLS EOF，尚未上传，PR1未合并。
- 当前Clashmi代理节点向上游返回xhttp 411；本地混合端口7890同故障。DIRECT核心连接测试可达GitHub/ChatGPT，但未更改全局代理配置。已通过异步问题询问用户是否切网，独立准备继续。
- V2执行前修订、runtime_identity、analysis_plan已写定；不额外做160次筛选。
- 各代理有独立写入范围，root不能 checkout G 分支直到 legacy_task1_fix 完成并交付。

- legacy任务1独立本地分支 codex/legacy-branch-integrity-2026-11-07，提交3c3dd9ac01cfca296b0cc4a7088ecda5b17d41e3，14tests通过。G已切回pilot分支77cca53。旧PR和task1推送都待网络恢复。
- 80题初稿通过32 oracle+24状态检查；root要求去除教学式提示，作者正在执行结果前修订；匿名包需重生成。
- 58项v2离线测试通过；v2_preflight_audit 独立复核中；v2_figures 编写结果脚本。
- 已询问用户是否允许临时GLOBAL切DIRECT（影响全机所以需明确答复），未获回复前不改变代理。

## 最新准备状态
- 网络已自行恢复（GitHub/ChatGPT HTTP200），root未修改任何代理设置；之前两个网络问题无需用户回答，不存在待审批动作。
- PR1已squash合并到original main：824d5d4ed36d2bf6246c91481b02e49146378f8c，source head77cca53。Fork仍保留。
- legacy修复追加零分母NA和5个CLI集成回归，本地head813ebb394661525e5580dee0ab21d733f2b53484；19tests通过，真实历史88组616行集成通过，raw/scored36文件SHA未变。独立任务venvlegacy_validation_venv，实际验证输出legacy_validation/。
- 题库全80匿名审动作80一致，但M03两个decisive题许可措辞不唯一；正式运行前修订10个M03公开题，oracle/keys不变；同reviewer复审10题全唯一。聚合和原始两轮证据在audits/，case_review.json已通过。
- 工具链独立预审发现缺失usage假0、异常sessionlifecycle、计划外raw漏报，均修；另修无final暂停后成功评分回归。最终67项offline tests通过，v2_preflight_audit复审中。未freeze、真实calls0。
- 图/报告脚本已准备，只能全800终态后运行；viewer已适配160group800response。冻结后不可更改harness/cases/protocol。

## 正式冻结
UTC 2026-11-06T20:39:12.653283+00:00
freeze SHA256 f5f73d297f3cc6b3f4049770dc6688a2ddc72ca66a784a89fd712d9c243afaf1
独立预审67tests及对抗探针PASS；已获用户许可必要时临时直连并结束后恢复，目前网络正常，未改代理。

运行已启动：exec_command session_id=34726，python -u harness/runner.py --phase dev --part all --workers 3，通过tee写execution.log（runs目录之外）。不要启动第二个writer；用write_stdin轮询这个session。阶段自动160P0之后640review。

- 正式运行2026-11-06 20:46 UTC已70/800 complete，全P0，0失败0重试，exec session34726继续运行。PR4已创建 https://github.com/18795892292tpy-collab/verification-mechanism-study/pull/4 ，head813ebb3；独立legacy_pr4_review发现2项条件/plan校验遗漏，legacy_task1_fix正在G分支修复，尚勿合并。v2_final_audit正在准备独立最终审计脚本，完成后需followup真实复算。

## 发布收尾已完成的部分
- PR4已squash合并，原main最新 ada83b5cadc91e30e0eade3256c4c6d2420fa8b2；head d1b10ec6f8345120bcef79ba98a9898dda5e3a7c。36项测试+独立20项复查，历史源记录未改。Issue2已关闭，说明comment6695586268。
- G现位于 codex/verification-v2-fixed800-2026-11-07（base ada83b5），仅未提交.gitignore/.gitattributes加入v2 allowlist；还没有复制或提交本次实际V2。
- 160个P0已全部complete且160/160正确，P0_DIAGNOSTIC.json只作已预定诊断，不筛题。640reviews继续，session34726仍活跃。
- 最终审计agent v2_final_audit 已准备脚本，800完后必须followup同reviewer。源码使用 --final --write，新建audits/INDEPENDENT_FINAL_AUDIT.json；archive只读 --archive-root。
- v2_figures正在适配冻结CSV新增usage resource字段，800终态前不生成图/报告。

## 运行中续接检查点（2026-11-06 21:31 UTC）
- exec session **34726** 正常运行，405/800 complete（P0=160、P1=60、P3=60、P7=64、P8=61），0失败0重试，3个在途调用。
- 不启动第二个writer，不修改任何冻结文件，不重抽任何已有final。使用write_stdin(session_id=34726)监测并保留exit状态；analysis/progress.py为派生进度可运行。
- 冻结SHA256 f5f73d297f3cc6b3f4049770dc6688a2ddc72ca66a784a89fd712d9c243afaf1；28个文件。67项工具链测试及独立预审PASS。P0全部160正确已在P0_DIAGNOSTIC.json诊断，仍必须完成全部640复核。
- network正常，未修改代理；用户已允许必要时临时直连且结束恢复，但尚未使用该授权。

## 800结束后必须完成
1. 确认session退出0及800终态；python harness/runner.py --verify，python harness/evaluate.py dev；保存最后PROGRESS后停止写它。
2. analysis/plot_results.py / write_report.py / build_viewer.py；node analysis/check_viewer.cjs。v2_figures已适配最新CSV和usage空值，后续followup它用真实数据出图、视觉审查4张PNG，manifest.visual_review必须实际通过后改passed。
3. followup v2_final_audit：只提供文件路径，请它运行独立审计及人工核验。命令 audits/independent_final_audit.py --final --write（标准库，拒绝覆盖），成功产audits/INDEPENDENT_FINAL_AUDIT.json。整体WARN可因same-family/模拟限制，确定性完整性须PASS。保留最终审查trace/报告。不向reviewer灌输预期结果。
4. 核验所有图/报告实际数字，view_image真实图片；viewer测试必须800responses/160groups且无外网和JS错。case审查虽通过仍不是外部教育专家。
5. 更新本状态为实验完成/待发布，再运行analysis/package_results.py，生成中文README、运行依赖说明、FILE_MANIFEST与本地ZIP。GitHub只提交解包文件、不重复提交ZIP。打包后不要再改清单覆盖的文件；GitHub发布状态写外层目录。
6. G=/home/grf/Desktop/Codex_Verification_Experiment_2026-11-06/github_publish/verification-mechanism-study，当前branch codex/verification-v2-fixed800-2026-11-07，base ada83b5，只有.gitignore/.gitattributes两处未提交v2 allowlist。将完整V2复制到G/experiments/codex_verification_v2，排除__pycache__/runtime_empty/锁/tmp/pyc；比对manifest和staged Git blob原始字节。
7. 更新G README/AGENTS正式例外及旧report/dev_report.md新节/主张表，明确固定800为执行前偏离、无外部专家、不得由天花板证明优势或等价。不要改v1冻结记录/历史raw。
8. commit、push到原仓库分支，创建并attach新PR，核验远端head/关键文件/全部blob或fetch一致性，按授权收尾合并（期望head SHA）。GitHub连接器写403，本机gh账号jupiternaut有write；REST gh api --input JSON或--body-file避免Classic Projects bug。
9. 更新Issue3最终结果/执行前修订与范围，不能把额外筛选或专家审阅说成完成。旧Issue2已因PR1/4修复而关闭。Fork按用户选择保留，禁止删除。

已完成的原仓库PR1 merge824d5d4、PR4 mergeada83b5；PR4最终head d1b10ec，36tests+20项独立复查，所有历史记录未改。当前V2还未提交GitHub，不能提前声称完成800或发布成功。

## 用户授权并发修订（2026-11-07）
- 用户两次要求加并发；原3并发于667/800完成后安全停止，SIGINT仅Python父进程，旧session34726 exit130；667 attempts全部封存，0在途、0失败，既有final禁止重抽。
- 6并发从未运行；新非冻结driver将剩余133任务直接提高为12并发。原冻结28文件及baseline SHA不变，执行中修订及667份prior record哈希在protocol/CONCURRENCY_AMENDMENT_2026-11-07.json，待独立并发审核后启动。性能报告须明确3→12阶段变更。

- 并发独立审核PASS；12并发正式续跑已于2026-11-06T22:17:16 UTC启动，新exec session78670，命令python -u harness/run_concurrency_override.py --part all | tee execution_concurrency12.log。请只监测该writer。原session34726已exit130。

## 最终执行状态（2026-11-06 22:22:43 UTC 完成）
- 原3并发完成667后按授权安全停机，12并发session78670继续剩余133，最终exit0。
- 800计划任务/800完整记录/800实际调用/800独立会话，0失败0重试；P0/P1/P3/P7/P8各160。不得再启动模型。
- runner --verify与evaluate通过，原28冻结文件未改；五程序action全部160/160，首轮自然错误0、条件修复率NA；I78/I73均0。仅说明该模型/题库天花板，不支持机制优势或等价。
- 独立原始复算确定性完整性PASS；semantic同模型家族/内部暂定，整体WARN。外部教育专家/真实人类/确认集未做。
- 四组图及来源清单已实际视觉审阅pass；viewer160组800回答自动检查通过（桌面/手机真实截图、无外网/JS错误/横溢）。
- 网络配置全程未被root修改，无需恢复代理；用户授权的直连后备未使用。
- 归档后不再改本目录清单文件。GitHub发布状态另写父目录v2_publication/，该目录作为原始规范实验保留，G副本仅用于发布/归档复算不伪装原主机执行。
