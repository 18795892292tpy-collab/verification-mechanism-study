# V3 作者记录

- 主机与规范路径：liekkas，`/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3`。V2只读，没有模型调用或修改已有回答。
- 已读本地AGENTS、仓库verification-case-builder技能和hard_tier；本批依用户授权、根协议执行开发性80题预试和条件草稿挑战。没有外部专家，不能称确认集。
- 草稿与答案依据均在被试运行前编写。先定义制度、事实和语义动作，再映射选项字母。初始全族纯循环映射无法实现本批不同语义方向的20/20/20/20平衡；生成成功前改为按每族基础/变化语义分别对应轮换字母。此选择只依预定结构化key，不读取被试结果。
- 初版生成后，在不改变公开题或草稿的条件下，增强逐选项排除说明与R05—R08可执行规则推导，新增R08等号边界测试。原builder、keys和真值表保存在`author_revisions/initial_before_explicit_exclusions/`。公开运行输入SHA保持不变。
- 每一错误草稿是作者标定的单一推断错误，`single_error_mechanism`给出其机制；这尚需独立盲审核对，不能把作者标定说成外部专家发现。程序只检查结构与规则一致性，不宣称自动验证所有自然语言逻辑。
- 缺失状态不删除一般字典里的所有候选值，只删除唯一的实体与值的关联记录；两种候选补全均应产生不同实体行动，所以必须补取。需盲审者检查备忘录及其余来源是否意外泄漏该关联。
- 当前公开长度约974—1088字；未采用长档案操作，没有宣称难度高于V2或保证自然错误出现。P0若天花板须保留结果并按根协议停止本路线扩量。

- 冻结前引用完整性修订：M05/M06/R08的草稿解释使用S7来源，但原引用列表未包含S7。为避免正确/错误条件的引用数量差异，对全部32份挑战稿统一补列S7（均为6个来源），无其他档案/行动/理由/信心变化。原版本保存在`author_revisions/before_challenge_citation_completion/`，精确差异验证见`challenge_citation_revision.json`。P0输入SHA保持4120eca4a589a6e1ba9c75c0ef0e0f5f11ed11604d4195ddf35d65fb252dc708。

- 匿名审题后的冻结前有限修订：R06 paraphrase两题将S1“已完成”改为“已通过”以保持原审计条件，修复备忘录“须急”为“应急”；R05 missing两题把S4缺页字段名“停表公文类别”改为中性“N18公文类别”。其余76题及全部32挑战稿逐字节不变，所有P0答案键语义不变（仅受影响public SHA更新）。旧版副本与逐题diff分别在`author_revisions/pre_blind_corrections_R05_R06/`、`blind_revision_R05_R06.diff`；机器差异证明见同名JSON。须由匿名审题者复审这4题后再冻结。
