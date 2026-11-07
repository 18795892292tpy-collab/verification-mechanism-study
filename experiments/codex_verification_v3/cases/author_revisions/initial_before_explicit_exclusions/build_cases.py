#!/usr/bin/env python3
"""V3 authored synthetic cases; standard library only, no model calls or output-derived keys."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import json, hashlib
R=Path(__file__).resolve().parents[1]
assert R==Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
S=['base','decisive_change','irrelevant','paraphrase','missing']
F=[]
def add(**kw): F.append(kw)
add(id='M05',kind='material',title='明洲学校：三年设备维护合同',levers=['multi_hop','calculation'],
 actions=['按三年必付总额提交委员会会签，暂不由单部门签约','按三年必付总额由设备部门直接签约','只签第一年并把余下两年留在同一不可撤销承诺内','补取本包一次性部署费归档页后再定签署路径'],
 base=12000,changed=2000,key_base=0,key_changed=1,critical_name='部署费',
 sources=[
 ('签署办法','固定承诺期必付总额达到100000元的合同须委员会会签，未达到的须由设备部门签署。支出完整且界线明确时不得另走补证路径。不可撤销的三年承诺不得按年度拆成三个签署决定。'),
 ('支付口径','总额包括固定承诺期全部维护费及一次性必付部署费；可撤销的选购项目不计入。本合同每年费用按前一年乘1.05，计算保留元以内小数；本题所有金额均为含税应付数，无其他费用。'),
 ('合同与索引','合同Q72约定不可撤销服务期三年，首年维护费30000元；二、三年按支付口径递增。附件索引：主机包P8的一次性部署费只在清单D9记载。便携扩展包为完全可取消选项，不购买也不影响主机包运行。'),
 ('部署清单D9','主机包P8的一次性必付部署费为{value}元。此页只载该费用，不含任何年度维护费。'),
 ('采购请求','本次仅购买主机包P8的固定三年服务，不购买便携扩展包。付款时点是年初，但签署时三年支付义务一次成立；没有已获委员会会签的记录。'),
 ('预算通知','设备维护年度预算为42000元。预算用于安排现金支付，不调整签署办法的固定承诺期总额口径。财务已确认款项来源合法，预算来源不构成额外暂停条件。'),
 ('厂商报价封面','报价封面显示首年维护30000元，便携扩展包另价18000元；封面未写主机包部署费。厂商说明各附件按合同索引归档，首年报价不覆盖全部固定承诺。'),
 ('交付安排','技术组希望在秋季学期第二周完成培训。培训由现有维护人员承担，既不增减合同必付费用，也不改变三年承诺。'),
 ],
 paras={0:'签约权限按完整承诺期的必付款核定：达到100000元交委员会会签；低于该数由设备部门签署。信息齐备时须按该界线办理。仍保留三年不可撤销义务的年度拆签不获允许。',1:'核算须加总承诺期内各年维护和一次性强制部署支出，能无条件取消的选购项排除。年度维护依次为上一年金额的1.05倍；所列数值已经含税，本案无其他应付项。',3:'D9归档记录：主机包P8须一次缴付部署费{value}元；各年度维护费用另按合同计算，不包含在该数中。',6:'报价首页列出第一年维护30000元及可选便携包18000元，没有列主机部署费。其他款项需按索引查看附件，首页报价并非三年固定承诺总价。'},
 reason_base='三年维护合计94575元，加D9部署12000元为106575元，达到100000元；选购包不在请求范围，应提交委员会会签。',
 reason_changed='三年维护合计94575元，加D9部署2000元为96575元，未到100000元；选购包不在请求范围，应由设备部门签约。',
 error_base='按合同三年维护合计94575元核定签署层级，D9的一次性部署属于开通项目而不计入固定承诺总额；未达到100000元，应由设备部门签约。',
 error_changed='三年维护合计94575元，加D9部署2000元及封面便携扩展包18000元为114575元；将封面选购项目计入本次固定承诺，应提交委员会会签。',
 error_mechanisms=['错误排除题内支付口径明确要求计入的一次性必付部署费，其他维护计算正确。','错误把未购买且可撤销的选购包纳入本次材料范围，其他费用计算正确。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S2','S7'],
 memo_base=['应按完整承诺期与本包必付支出核定层级，年度封面并非合同总额；本案达到会签界线，提交委员会会签。','应以报价封面与三年维护合计核定层级，一次开通项目另行归类；本案未到会签界线，由设备部门签约。'],
 memo_changed=['应按完整承诺期与已请求项目核定层级，可取消扩展包不纳入；本案未到会签界线，由设备部门签约。','应按报价封面所列完整服务组成核定层级，将扩展包一并计入；本案达到会签界线，提交委员会会签。'])
add(id='M06',kind='material',title='澄湾学校：咨询数据包外发',levers=['multi_hop','version_chain'],
 actions=['按已匹配审查的脱敏包执行外发','将待发包退回重新完成脱敏审查，本次不外发','仅改文件名后按原审批外发','补取待发构建号对应的摘要记录后再决定'],
 base='7f31a8d4',changed='0c92b6e5',key_base=1,key_changed=0,critical_name='构建摘要',
 sources=[
 ('外发规则','本次咨询用途已获批准。待发包只有与“通过”隐私审查记录的内容摘要完全相同，才须放行；与“未通过”记录相同则须退回重审。文件名、作者或生成日期均不代替内容摘要；不得仅改名放行。'),
 ('摘要和构建索引','构建号指向一个完整内容快照，清单只用不可变摘要识别该快照。同名文件可以对应不同摘要；对审查记录的结论应用于匹配摘要的整个包，不能因同名而互换。'),
 ('传送请求','实际待传构建为B61；文件名“咨询匿名表.csv”，接收方和用途均在当前批准范围内。档案管理员指定清单E23是B61的唯一内容摘要来源，发布任务尚未执行。'),
 ('清单E23','构建B61的完整内容摘要为{value}。此记录不包含任何审查结论。'),
 ('审查登记','摘要7f31a8d4：未通过，包内附带可稳定关联个人的连接表。摘要0c92b6e5：通过，连接表已移除且仅保留批准字段。两份登记均已由同一有权审核组签署，没有其他适用于本案的摘要记录。'),
 ('文件历史','B58与B61均沿用“咨询匿名表.csv”文件名。B58已在早期审查会上展示；此处没有提供B58的内容摘要。最新构建号不自动表示新增隐私问题，也不自动表示问题已修复。'),
 ('项目审批封面','封面写明“咨询匿名表.csv可用于批准的咨询目的”，并要求具体传输遵守内容摘要审查。封面记录的是用途许可，不是特定构建的内容检查结论。'),
 ('接收安排','接收方希望周三上午收到表格。传送路径已加密且接收名单完整；时段偏好不改变内容匹配要求。'),
 ],
 paras={0:'在用途获准的前提下，匹配已通过审查的内容摘要就应外发，匹配未通过的摘要则退回重审。该匹配要求针对内容而非名称、人员或时间，更名本身不能令待发包通过。',1:'每个构建编号对应一个不可变的完整内容快照，快照由摘要唯一识别；文件重名不意味着内容相同。审查意见只能用于摘要相同的整包。',3:'E23只登记构建B61的内容标识：{value}；审核是否通过须另查审查登记。',6:'用途许可封面允许名为“咨询匿名表.csv”的资料服务该咨询项目，但同时要求每次传输按内容摘要审查。封面批准不等于已审核某个构建的实际内容。'},
 reason_base='E23把待发B61关联到7f31a8d4，S5对此摘要标为未通过；同名用途许可不能替代内容审查，本次退回重新脱敏审查。',
 reason_changed='E23把待发B61关联到0c92b6e5，S5对此摘要标为通过，接收用途已批准；满足精确内容匹配，应执行外发。',
 error_base='B61沿用审批封面的“咨询匿名表.csv”文件名与批准用途，因此将S7的用途许可视为该构建已通过内容审查，应执行外发。',
 error_changed='E23所列0c92b6e5沿用旧版文件名，因此将S5中7f31a8d4的未通过结论沿文件名继承给B61，本次退回重新审查。',
 error_mechanisms=['把名称/用途许可替代具体内容摘要审查，其他待发编号与用途事实不变。','把另一摘要的未通过结论沿同名文件错误转移，混淆内容级证据适用对象。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S5','S7'],
 memo_base=['用途许可须与内容审查分别核对，封面同名不足以覆盖当前构建；本案匹配未通过记录，应退回重审。','用途许可与文件名称在本次传输中保持一致，封面许可覆盖当前构建；本案已满足许可条件，应执行外发。'],
 memo_changed=['用途许可与内容摘要均须匹配归档记录，不能继承同名旧包的结论；本案已通过审查，应执行外发。','用途许可仍须满足旧包审查所指出的要求，同名构建延续该审查结论；本案仍未通过，应退回重审。'])
add(id='M07',kind='material',title='竹溪学校：阅读支持筛查工具',levers=['multi_hop','calculation'],
 actions=['采用该工具用于校内阅读支持初筛','保留现行人工初筛，不采用该工具','只因总体准确率较高就采用该工具并免除复核','补取匹配验证组的检出人数记录后再决定'],
 base=46,changed=48,key_base=1,key_changed=0,critical_name='风险组检出人数',
 sources=[
 ('工具采纳标准','须同时满足：在适用验证组中，已确认需要支持者的漏识别率不高于5%，且不需要支持者的误报率不高于20%。满足则采用，不满足则保留人工初筛。总体准确率不能替代两项分组指标；采用后仍保留规定的人工复核。'),
 ('指标口径','漏识别率=(确认需要支持人数−其中被工具标记者数)/确认需要支持人数。误报率=确认不需要支持者中被工具标记者数/确认不需要支持人数。每人只有一次有效结果，不能用所有验证者作漏识别分母。'),
 ('样本匹配表','本校对应验证分层V4，其他分层不进入决定。V4独立人工参照确认需要支持50人、不需要支持150人；工具记录以登记T26关联该分层。'),
 ('登记T26','V4确认需要支持的50人中，工具标记了{value}人。该数只记风险组检出，不含误报。'),
 ('无支持需求组记录','同一V4中，确认不需要支持的150人里有5人被工具标记。记录已完备，没有重复受测者或丢失随访。'),
 ('其他分层说明','V2采用不同阅读材料，样本更大，报告评价较好。本校课程映射只支持V4；厂商未请求把V2和V4合并作为新验证组。'),
 ('宣传材料','产品在大多数验证者身上能作出符合人工参照的分类，整体一致表现良好。宣传页不把总体表现写成漏识别率，也未取消学校的双指标采纳标准。'),
 ('培训安排','图书组希望培训演示使用纸质讲义。演示载体不改变本校映射组和两个指标的定义。'),
 ],
 paras={0:'本校必须同时核查适用组中的两项门槛：确认需支持者漏标至多5%，确认无需支持者误报至多20%。两项皆达标须采用，否则维持人工初筛；总体准确度和免复核都不能替代该程序。',1:'漏标比例的分母是确认需支持的人数，分子是其中未被工具标记者；误报比例则在确认无需支持者内计算。验证样本总人数不是漏标指标的分母，每人计一次。',3:'T26对应V4：人工确认需要支持的50人内，有{value}人获得工具标记；这一栏不统计无需支持者。',6:'宣传页称多数验证对象的机器分类与人工判断一致，整体表现良好；该描述没有提供可替代漏识别门槛的许可，学校仍按两项分组标准采纳。'},
 reason_base='V4漏识别率为(50−46)/50=8%，超过5%；误报5/150约3.33%虽合格，但两条件须同时满足，应保留人工初筛。',
 reason_changed='V4漏识别率为(50−48)/50=4%，误报5/150约3.33%，均在门槛内，应采用工具并保留规定人工复核。',
 error_base='V4未检出的4人在全部200名验证者中占2%，将此作为漏识别率；误报5/150约3.33%，两项满足门槛，应采用工具。',
 error_changed='将V4误报的5人也计入需支持者的漏识别分子，得到(50−48+5)/50=14%；误报率仍为5/150，应保留人工初筛。',
 error_mechanisms=['用全部验证样本而非需支持组作为漏识别分母，混用指标适用人群。','把不需要支持组的误报事件转入需要支持组的漏识别分子，混用事件统计对象。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S2','S7'],
 memo_base=['分组指标须按各自适用人群核算，整体表现不能抵消风险组漏识别；本案漏识别未达标，应保留人工初筛。','分组指标可由总体漏标人数占全样本比例衡量，整体表现印证其可靠性；本案符合两项要求，应采用工具。'],
 memo_changed=['分组指标须把漏识别和误报分别归入对应人群，不能跨组累加事件；本案两项均达标，应采用工具。','分组指标须把所有异常分类都纳入需支持组的漏识别负担，避免漏计；本案漏识别未达标，应保留人工初筛。'])
add(id='M08',kind='material',title='栖原学校：教学方案证据汇总',levers=['multi_hop','persuasive_precedent'],
 actions=['将方案纳入正式长期实施','仅批准一轮限定试用，保留评估','将两篇同队列分析拆成两个独立验证队列后长期实施','补取第二篇报告的注册队列对应记录后再定层级'],
 base='C41',changed='C59',key_base=1,key_changed=0,critical_name='第二报告队列登记',
 sources=[
 ('采纳等级办法','有至少两个独立受试队列各自达到效果和完成率标准时，须长期实施；仅有一个合格独立队列时，须限定一轮试用。两篇报告、不同作者或不同分析方法不能把同一批受试者变成两个独立队列；不得人为拆分注册队列计数。'),
 ('证据单位规范','独立性以注册队列号判定。相同队列号表示同一批受试者，即使指标或文章不同也只计一个；不同队列号在本档案中已核实无人员重叠。合格标准为增益至少5分且完成率至少85%。'),
 ('第一报告','文章A12的注册队列为C41，匹配本校年级与课程；增益7分，完成率92%。其注册材料完整，由机构甲分析。'),
 ('第二报告注册对应','文章B37对应的注册队列号为{value}。这里只登记文章与队列的对应，不表示效果大小。'),
 ('第二报告与注册库','B37也匹配本校年级与课程，增益6分，完成率90%，由机构乙重新分析。注册库中C41和C59均已审核，且C41与C59人员互不重叠；本案只使用A12和B37两篇报告，不另引入其他效果证据。'),
 ('发表记录','A12与B37发表于不同刊物，文章编号、作者名单和统计方法均不同。注册队列号需要由各自对应记录核对，发表记录不含新的受试者身份信息。'),
 ('历史采纳记录','上一项目依据两篇文章长期实施；其附件记载两篇文章来自两个不同且无人员重叠的注册队列。该记录没有允许以后仅凭文章篇数判定独立性的内容。'),
 ('教研安排','教研组希望在季度会议上展示两篇报告的封面。展示页数不改变证据单位或本次采纳等级。'),
 ],
 paras={0:'正式长期实施需要至少两个互相独立、各自达标的受试队列；只确认一个合格队列时按规定先试用一轮。出版物数量、作者更替和分析差异不增加独立受试队列，同一注册队列不得拆开凑数。',1:'本档案以注册队列编号识别独立性：同号是同批受试者，异号已确认无交叠。每个队列须达到增益5分以上（含5）和完成率85%以上（含85）两门槛。',3:'注册对应页记录B37的队列标识为{value}；该页不登记效果指标。',6:'此前长期实施的项目确有两份报告，但其附件还确认了两个互不重叠的独立队列；先例并未把两篇文章本身当成独立性证明。'},
 reason_base='A12和B37都对应C41，虽效果与完成率均达标且文章不同，独立受试队列仍只有一个；应限定一轮试用。',
 reason_changed='A12对应C41、B37对应C59，注册库确认两队列无人员重叠，且两报告各自达标；已有两个独立合格队列，应长期实施。',
 error_base='两篇报告分别由机构甲、乙分析，文章编号和方法不同，因此按两个独立证据队列计数；两项效果均达标，应长期实施。',
 error_changed='A12与B37都匹配本校同一年级和课程，因此将C41与C59合并视作同一个受试队列；达标独立队列只有一个，应限定试用。',
 error_mechanisms=['把文章/作者独立误作受试队列独立，仅错在证据计数单位。','把研究目标人群相同误作实际受试者队列相同，仅错在队列归并依据。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S2','S7'],
 memo_base=['采纳等级按注册队列而非文章篇数核定，先例还要求受试者独立；本案只有一个独立达标队列，应限定试用。','采纳等级可按不同作者和文章分别核定，先例也是两篇报告共同支持；本案有两个独立证据，应长期实施。'],
 memo_changed=['采纳等级按注册队列和人员独立性核定，共同课程不取消受试者独立；本案具备两个达标队列，应长期实施。','采纳等级须把对应相同年级课程的报告归为一个队列，避免重复计算；本案仅有一个独立证据，应限定试用。'])
add(id='R05',kind='rule',title='南岑学校：材料补正时限',levers=['multi_hop','calculation'],
 actions=['受理本次补正，继续原申请','以超过补正期限结案，本次不继续原申请','把所有往来邮件日期都从时限中扣除再受理','补取登记N18的公文类别代码后再核算时限'],
 base='Z1',changed='X2',key_base=0,key_changed=1,critical_name='停表公文类别',
 sources=[
 ('补正规则','申请自送达次工作日起算，补正须在第5个计时工作日结束前送达，含第5日；否则结案。只有公文登记类别Z1的正式补正通知才暂停计时，从发出当日至恢复通知前一日均不计。X2咨询函不暂停，即使文字讨论同一材料。'),
 ('计时日历','本案日期均在同一周至下一周：6月1日星期一至6月5日星期五为工作日；6日、7日为周末；8日星期一至10日星期三为工作日，无假日。恢复通知当日恢复计时。'),
 ('送达与流水索引','原申请6月1日送达。流水号N18对应6月3日发出的公文；恢复通知6月8日发出；本次补正在6月10日当日结束前送达。N18的公文类别只见S4登记页。'),
 ('N18登记页','6月3日公文N18的类别代码为{value}。该页没有改动送达或恢复日期。'),
 ('类别说明','Z1是正式补正通知，X2是咨询函；两者均可能写“材料待补正”“请补交附件”。类别由有权登记页确定，主题相同或出现相同用语不改变类别。'),
 ('申请情况','所有补正材料在6月10日送达时均已齐全，无签名争议，无其他中止、中断、撤回或延期事由。本次只按补正规则决定继续还是结案。'),
 ('往来邮件','6月3日公文正文讨论附件的格式及“待补正”事项，6月8日通知继续往来处理。邮件正文没有另列公文类别代码；申请人希望这些日期能够从期限中扣除。'),
 ('归档安排','档案室拟把邮件打印成双面纸。打印方式不影响工作日、登记类别或材料送达时间。'),
 ],
 paras={0:'计时从申请送达后的首个工作日开始，第5个计时工作日结束前补正有效，超期则结案。停表必须由登记为Z1的正式通知触发，发出日计入停表区间，恢复日前一日为末日；登记X2的咨询不触发停表。',1:'日历核实6月1—5日及8—10日均是工作日，6—7日为周末，没有额外假日。计时在恢复通知发出的当天重新开始。',3:'公文登记将N18（6月3日发出）归入{value}类别；送达与恢复时点仍按流水记录。',6:'函件使用“待补正”等表述谈及附件格式，之后有恢复往来的通知；这些正文未载类别代码，申请人主张扣除该段时间。'},
 reason_base='N18登记Z1，6月3日至7日停表；计时工作日为2日、8日、9日、10日共4日，补正未超过第5日，应受理继续申请。',
 reason_changed='N18登记X2，不触发停表；计时为2、3、4、5、8、9、10日共7个工作日，超过5日，应结案。',
 error_base='N18虽登记Z1，但函件正文讨论的是附件格式，因此将其按一般咨询而非正式停表通知处理；计时7个工作日，超过5日，应结案。',
 error_changed='N18登记X2，但正文写有材料待补正，因而把该表述作为停表触发；扣除3日至7日后计时4个工作日，应受理。',
 error_mechanisms=['用正文议题否定已满足的正式Z1停表触发条件，后续不暂停计时计算一致。','用后果性描述“待补正”替代Z1类别触发条件，后续暂停计时计算一致。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S1','S7'],
 memo_base=['期限须先按登记类别确认是否触发停表，正文议题不改正式效力；本案应扣除停表区间，补正有效，应继续申请。','期限须按正文事项判断是否实质触发停表，附件格式属于一般咨询；本案应连续计时，补正超期，应结束申请。'],
 memo_changed=['期限须先按登记类别确认是否触发停表，“待补正”字样不足以触发；本案应连续计时，补正超期，应结束申请。','期限须按正文是否要求补正判断停表，公文已明确存在待补正事项；本案应扣除该区间，补正有效，应继续申请。'])
add(id='R06',kind='rule',title='云桥学校：过渡拨款例外',levers=['multi_hop','authority_chain'],
 actions=['给予一次过渡拨款，额度按已核定金额执行','转入常规补件流程，本次不发过渡拨款','把应急登记视为所有条件全豁免，直接发全年款','补取本次支出科目归类记录后再决定'],
 base='E2',changed='C1',key_base=1,key_changed=0,critical_name='例外适用支出类别',
 sources=[
 ('过渡拨款规则','外部批复仍待办且上周期审计已通过的，给予一次过渡款。若上周期审计尚未完成，只有“有效应急登记”与“本次支出属于C1连续课程”同时满足时，才豁免审计条件；E2设备更新不在此例外内。其他已知不满足者转常规补件。'),
 ('优先与边界','逾期追缴款未结清者一律不得拨过渡款，该禁止不受应急例外影响。例外只免除上周期审计条件，不免除外部批复仍待办这一前提，也不把一次过渡款改为全年拨款。'),
 ('项目与索引','申请P43外部批复仍待办，上周期审计尚未完成；追缴账目已结清。申请有经有权机构核验的有效应急登记EM7。支出归类单L62关联P43，当前只缺对其类别值的核对。'),
 ('L62归类单','本次申请P43的支出类别代码为{value}。核定金额已确定，没有另列其他类别的支出。'),
 ('科目定义','C1指连续课程的直接实施支出；E2指设备更新支出。两类均可用于教学项目，但“用于教学”不使E2成为C1。类别由L62核定，本题没有另行修改归类的权限。'),
 ('登记授权','EM7是正式应急登记，不是申请人自行标注。登记审批机关可以核验应急状态，但没有扩张过渡拨款例外类别或免除追缴禁止的授权。'),
 ('项目说明','申请人强调该项目有助于教学连续性，EM7也使用“保障教学衔接”的文字。说明没有替代财务归类单，也未授权把所有相关支出都认作C1。'),
 ('支付安排','财务拟在周五集中发送已批准支付指令。发指令的批次不改变本次资格与一次性额度。'),
 ],
 paras={0:'普通过渡款需同时有外部批复待办和已完成的上周期审计。审计未完时，只在有效应急状态且开支代码为C1时豁免该审计条件；E2不适用。已知不合资格则走常规补件，不拨本次过渡款。',1:'追缴款逾期未清的禁止优先于应急例外。获例外者也仍须批复待办，并只可获一次过渡额度；全年拨款和其他前提均未获豁免。',3:'归类单L62记录P43本次开支为{value}；核定金额对应且仅对应这一类别。',6:'申请说明和应急登记都提到教学衔接与连续性，但这些目的表述并非财务类别核定，不能把所有教学相关开支转换成C1。'},
 reason_base='P43批复待办、审计未完且有效应急登记，但L62为E2；例外要求应急且C1，E2不满足豁免，须转常规补件，本次不拨。',
 reason_changed='P43批复待办、审计未完且有效应急登记，L62为C1，追缴已结清；符合审计条件豁免，给予一次核定过渡款。',
 error_base='P43批复待办且具有有效应急登记，因此把应急登记单独作为审计豁免的充分条件；追缴已清，应给予一次过渡款。',
 error_changed='P43虽有应急登记且L62为C1，但上周期审计尚未完成，因此仍把审计完成视为没有任何例外的必要条件，转常规补件。',
 error_mechanisms=['把合取的例外触发条件“应急且C1”错误扩大为仅应急。','遗漏已满足的明文例外，错误将一般审计前提绝对化。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S1','S7'],
 memo_base=['应急豁免须同时落入指定支出范围，教学目的文字不改变归类；本案不满足豁免，转常规补件，不拨过渡款。','应急登记已经确认保障教学衔接的需要，可独立触发审计豁免；本案满足过渡目的，应给予一次核定拨款。'],
 memo_changed=['应急状态与指定支出范围须一并核对，满足时适用明文审计豁免；本案符合例外，应给予一次核定拨款。','过渡拨款仍须先完成上一周期审计，应急与支出归类不能替代该项；本案审计未完，应转入常规补件。'])
add(id='R07',kind='rule',title='泠河学校：委员会会议决议',levers=['multi_hop','calculation'],
 actions=['确认本议项决议成立并登记通过','确认本议项未达法定人数，安排重新表决','将回避成员计入法定人数后登记通过','补取远程席位身份与实时状态记录后再判断'],
 base='V',changed='P',key_base=0,key_changed=1,critical_name='远程席位实时核验状态',
 sources=[
 ('会议规则','每个议项先排除回避成员，剩余有资格成员为法定人数分母。有效到会须达到该分母的三分之二，向上取整；不足即不成立，须重开表决。到会达标后，赞成票超过全部有资格成员的一半才通过。'),
 ('到会口径','现场签到的有资格者及经实时身份核验的同步远程者计入有效到会；回避者、录像回放者和仅提交票据者不计。每人只计一次。票据存在不反向证明其满足实时到会条件。'),
 ('本议项名册','全体成员甲乙丙丁戊己庚共7名，本议项甲、乙回避；现场签到为乙、丙、丁，远程席位为戊、己。庚未出席。戊已实时核验通过；己的状态见同步平台日志J63。'),
 ('J63平台日志','己的远程席位状态代码为{value}。席位已生成一张票据，但代码决定它是否属于同步实时到会。'),
 ('代码与投票汇总','V表示实时身份核验通过的同步参加，P表示观看录像且不构成同步参加。丙丁戊各投赞成票，己投反对票；名册与票据都没有其他成员，没有额外回避或弃权。'),
 ('票据归档','系统给戊、己分别保留电子票据，也给现场票据编号。票据号用于追踪意见，会议秘书仍需按到会口径判断法定人数和有效表决资格。'),
 ('会议简报','简报写“现场三人、远程两席位，收到四张本议项票据”。这是未经法定人数归类的原始数量汇总，不含J63的状态代码。'),
 ('会议后勤','会议室预留十个座位，摄像机计划下午归还。座位容量与器材安排不改变议项回避和到会资格。'),
 ],
 paras={0:'法定到会人数逐议项计算：先从全体成员去除回避者，再取剩余人数的三分之二并向上取整。未达即须重新表决；达到后，赞成票还须严格超过剩余有资格成员的一半才可通过。',1:'有效到会仅包括有资格的现场签到成员和经过实时身份认证的同步远程成员。录像、回避及单纯持有票据均不算到会；每名成员只能计一次，票据不能替代实时状态证据。',3:'J63记载己席位的参加状态为{value}。该席位虽有票据，是否算实时到会仍由该代码判定。',6:'简报仅汇总现场3人、远程2席及本议项4张票，没有完成回避和同步状态分类，也未给出己的J63代码。'},
 reason_base='排除甲乙后有资格5人，法定到会ceil(10/3)=4；丙丁现场、戊己均实时有效，共4人。赞成3票超过5的一半，决议成立。',
 reason_changed='有资格5人，法定到会须4人；乙回避不计，己为P不计，丙丁戊有效到会仅3人，未达法定人数，须重开表决。',
 error_base='有资格成员仍按全体7人计算，法定到会须ceil(14/3)=5；有效到会丙丁戊己只有4人，因此未达法定人数，须重开。',
 error_changed='有资格5人、法定到会须4人；将己已提交的票据视为实时到会凭据，连同丙丁戊共4人，赞成3票，确认决议成立。',
 error_mechanisms=['未从法定人数分母剔除已回避成员，其他有效到会及赞成数正确。','由票据这一后果倒推己满足实时到会触发条件，其他分母和票数正确。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S1','S7'],
 memo_base=['法定人数须先排除回避成员，再对远程席位作实时资格核验；本案有效到会和赞成票均达门槛，应确认通过。','法定人数应按委员会全体人数保持固定，不因单个议项回避缩减；本案有效到会不足该门槛，应重新表决。'],
 memo_changed=['法定人数须先排除回避成员，并把录像席位排除在实时到会之外；本案有效到会未达门槛，应重新表决。','法定人数可用已有票据证明对应席位已经参加本议项的表决过程；本案到会和赞成票均达门槛，应确认通过。'])
add(id='R08',kind='rule',title='鹿浦学校：内网故障事件分级',levers=['multi_hop','calculation'],
 actions=['按三次独立故障触发规则向区级平台上报','按不足三次独立故障作校内跟踪，不触发本次上报','按仪表原始告警条数直接上报而跳过事件归并','补取第二段故障开始时刻后再进行事件归并'],
 base='08:29',changed='08:31',key_base=1,key_changed=0,critical_name='第二段故障开始时刻',
 sources=[
 ('事件上报规则','同一设备在任意24小时观察窗内发生至少3次独立故障事件时须上报，否则仅校内跟踪。原始告警段先按归并规则形成独立事件，不能直接按告警条数触发。具有资料泄露标志者另有优先上报，但本案已核实无该标志。'),
 ('归并规则','按时间排序，同一设备前一段恢复到下一段开始的间隔不超过20分钟（含20）时，两段归入同一事件；间隔超过20分钟开启新事件。连续符合条件的段传递归并，结束时刻以最后一段恢复为准。'),
 ('设备及首末记录','同一设备N7在11月4日的第一段为08:00至08:10，第三段为09:00至09:05。第二段恢复于08:35，开始时间只见记录G24。观察窗为当日00:00至24:00，无其他告警段。'),
 ('G24记录','第二段故障在同日{value}开始，08:35恢复。该条和首末记录属于同一设备N7。'),
 ('日志完整性','三段都由同一监测时钟记录，已核实不存在丢段、时钟漂移、重复事件或资料泄露标志。记录顺序以实际开始时间确定，不以通知到达邮箱的先后排序。'),
 ('处置记录','每个告警段均完成恢复操作，所有业务现已正常。恢复完成并不取消已经发生的事件计数；只按规定间隔归并，也不把全天所有恢复段合并成一个事件。'),
 ('仪表摘要','仪表显示“本日告警3条，全部已恢复”。该计数按监测段逐条产生，仪表没有执行20分钟间隔归并，也未给出第二段开始的具体时刻。'),
 ('通知安排','办公室拟在下午汇总维护工单。工单提交时段不改变实际故障间隔或观察窗内事件数。'),
 ],
 paras={0:'上报门槛为同一设备24小时内至少3个独立事件，未达到则校内跟踪。必须先把告警段按规则归并，不能用条数替代事件数；资料泄露另可优先触发，但本案确认不存在。',1:'相邻段以前段恢复到后段开始的时间差判断：20分钟以内连同20分钟归为一个事件，大于20才另起事件。这个连接关系连续适用，同事件的结束取最后恢复时刻。',3:'G24所载第二段开始时刻是当日{value}，结束恢复时刻是08:35；设备仍为N7。',6:'摘要中的3条已恢复告警是原始监测段数量，未经过间隔归并；摘要没有登记第二段的实际开始时间。'},
 reason_base='第一段08:10恢复至第二段08:29相隔19分钟，归为一事件；08:35至09:00相隔25分钟，第三段另起，共2次，应校内跟踪。',
 reason_changed='08:10至08:31相隔21分钟，08:35至09:00相隔25分钟，两间隔均超过20，形成3次独立事件，达到门槛，应上报。',
 error_base='仪表记录三条告警并均已恢复，因此把每条已恢复告警直接视为一次独立事件，计3次，达到上报门槛，应上报。',
 error_changed='将同一设备当日恢复的各段视为同一已处置故障，不再按相邻间隔拆分；合为1次独立事件，不到3次，应校内跟踪。',
 error_mechanisms=['省略门槛前的告警归并条件，错把原始段数等同独立事件数。','把共同设备及已恢复状态替代20分钟归并条件，错误扩大归并范围。'],
 cite=['S1','S2','S3','S4','S5'],advice_cite=['S1','S7'],
 memo_base=['上报数量须由原始告警按相邻间隔归并形成，仪表条数不是最终事件数；本案独立事件不足三次，应校内跟踪。','上报数量可由每条已恢复告警分别确认，仪表已有三条完整恢复记录；本案满足三次故障条件，应向区级上报。'],
 memo_changed=['上报数量须按相邻恢复与开始的间隔逐段核对，已恢复不取消独立事件；本案达到三次门槛，应向区级上报。','上报数量应先把同设备同日已恢复的告警视作一次处置过程，防止重复统计；本案不到三次独立故障，应校内跟踪。'])

# Oracles derive semantic action solely from structured public facts.
def oracle(fid,value):
 if value is None:return 3
 if fid=='M05':return 0 if Fraction(30000)*(1+Fraction(105,100)+Fraction(105,100)**2)+value>=100000 else 1
 if fid=='M06':return {'7f31a8d4':1,'0c92b6e5':0}[value]
 if fid=='M07':return 0 if Fraction(50-value,50)<=Fraction(5,100) and Fraction(5,150)<=Fraction(20,100) else 1
 if fid=='M08':return 1 if value=='C41' else 0
 if fid=='R05':return 0 if value=='Z1' else 1
 if fid=='R06':return 0 if value=='C1' else 1
 if fid=='R07':return 0 if value=='V' else 1
 if fid=='R08':return 1 if value=='08:29' else 0
 raise ValueError(fid)

INTRO='以下为虚构学校内部封闭档案。制度只在本题成立，不代表现实法规。仅据已给材料，在四个完整行动中选择一个；不得补充档案外事实、擅改选项或增设审批条件。'
MISSING_RULE='[S9] 缺页处置与办理边界\n仅当本次分支判断所需的唯一字段未归档且不能从其他资料推出时，须选择补取该字段的行动；已知字段值不满足实体条件时按实体规则办理，不视为材料缺失。其余本案必要资料均已给出，没有题外禁止、额外权限或待核事实。'

def docs(f,state):
 value=f['changed'] if state=='decisive_change' else f['base']
 out=[]
 for j,(title,text) in enumerate(f['sources']):
  t=f['paras'].get(j,text) if state=='paraphrase' else text
  if j==3 and state=='missing':t=f'本次{f["critical_name"]}所在记录页尚未归档；本栏没有提供该字段取值，也没有可恢复它的备份。'
  else:t=t.format(value=value)
  if j==7 and state=='irrelevant':t='办公室改用电子工作纪要记录本次办理过程。此项归档载体安排不改变已给规则、事实、费用、时间或权限。'
  out.append({'id':f'S{j+1}','title':title,'text':t})
 out.append({'id':'S9','title':'缺页处置与办理边界','text':MISSING_RULE.split('\n',1)[1]})
 return out

def mapping(f_index):
 # Fixed whole-family rotation; semantic keys first, letters last.
 base=F[f_index]['key_base'];changed=F[f_index]['key_changed']
 return {base:'ABCD'[f_index%4],changed:'ABCD'[(f_index+1)%4],2:'ABCD'[(f_index+2)%4],3:'ABCD'[(f_index+3)%4]}

def dossier(f,state,mp):
 src=docs(f,state)
 options='\n'.join(f'{letter}. {f["actions"][semantic]}' for semantic,letter in sorted(mp.items(),key=lambda x:x[1]))
 text=INTRO+'\n\n'+f['title']+'\n\n'+'\n\n'.join(f'[{d["id"]}] {d["title"]}\n{d["text"]}' for d in src)+'\n\n可选行动（选择一项，不修改行动内容）\n'+options
 return text,src

def memo(f,state,advice,mp):
 if state=='missing':
  action=3 if advice=='aligned' else f['key_base']
  rationale=('应按缺页处置规则补取唯一决定字段，现有摘要与一般材料不能替代该记录；取得该页前暂不选实体办理路径。' if advice=='aligned' else '现有摘要与一般材料已给出足够业务背景，可以依通常适用情形直接办理；无需等待该记录，按所列实体路径处理。')
  refs=['S7','S9']
 else:
  changed=state=='decisive_change';key=f['key_changed'] if changed else f['key_base']
  action=key if advice=='aligned' else 1-key
  rationale=f['memo_changed' if changed else 'memo_base'][0 if advice=='aligned' else 1]
  refs=f['advice_cite']
 if state=='paraphrase':rationale=rationale.replace('本案','当前事项').replace('应','须').replace('核定','确定')
 text=f'建议：选择{mp[action]}（{f["actions"][action]}）。\n依据：'+ '；'.join(refs)+'。\n理由：'+rationale
 return text,action,refs

def write(path,value):
 p=R/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def main():
 items=[];keys=[];challenge=[];challenge_keys=[];truth=[];checks=[];lengths=[];ratios=[]
 for fi,f in enumerate(F):
  mp=mapping(fi)
  assert oracle(f['id'],f['base'])==f['key_base']
  assert oracle(f['id'],f['changed'])==f['key_changed']
  assert f['key_base']!=f['key_changed']
  for state in S:
   value=None if state=='missing' else f['changed'] if state=='decisive_change' else f['base']
   k=oracle(f['id'],value);body,sources=dossier(f,state,mp)
   reason=('决定字段未归档，实体分支不能唯一判定；S9要求补取该字段。' if state=='missing' else f['reason_changed' if state=='decisive_change' else 'reason_base'])
   reject={mp[n]:('符合唯一分支及办理边界。' if n==k else '该实体分支仍缺必要字段，不能代替S9补取动作。' if state=='missing' else '必要字段齐全，S9不允许把已知条件不满足改作缺页暂停。' if n==3 else '该选项与上述确定性分支或明确禁止条款冲突；参见规则与结构化推导。') for n in range(4)}
   truth.append({'family_id':f['id'],'error_type':f['kind'],'state':state,'facts':{'critical_value':value},'correct_semantic':k,'correct_action':mp[k],'reason':reason,'sources':sources,'option_analysis':reject})
   memo_len=[]
   for advice in ['aligned','flawed']:
    memo_text,advice_action,refs=memo(f,state,advice,mp);public=body+'\n\n建议备忘录\n'+memo_text
    item_id=f'{f["id"]}_{state}_{advice}';meta={'item_id':item_id,'family_id':f['id'],'error_type':f['kind'],'state':state,'advice':advice}
    items.append({**meta,'public_text':public})
    keys.append({**meta,'correct_action':mp[k],'correct_semantic':k,'advice_action':mp[advice_action],'pause_action':mp[3],'facts':{'critical_value':value},'reason':reason,'option_analysis':reject,'required_sources':f['cite'] if state!='missing' else ['S3','S4','S9'],'public_sha256':sha(public),'expert_review':'pending'})
    assert (advice_action==k)==(advice=='aligned')
    assert all(f'[{ref}]' in public for ref in refs)
    assert not any(x in public for x in ['flawed','aligned','key_base','正确答案','错误草稿','陷阱'])
    memo_len.append(len(memo_text));lengths.append(len(public))
   ratios.append({'family_id':f['id'],'state':state,'memo_length_ratio':max(memo_len)/min(memo_len)})
   if state in ['base','decisive_change']:
    changed=state=='decisive_change'
    for condition in ['correct','error']:
     action=k if condition=='correct' else 1-k
     rationale=f[('reason_' if condition=='correct' else 'error_')+('changed' if changed else 'base')]
     assert len(rationale)<=180
     draft={'action':mp[action],'cited_sources':f['cite'],'brief_justification':rationale,'confidence':5}
     draft_text=json.dumps(draft,ensure_ascii=False,separators=(',',':'))
     cid=f'{f["id"]}_{state}_draft_{condition}'
     meta={'item_id':cid,'family_id':f['id'],'error_type':f['kind'],'state':state,'draft_condition':condition}
     challenge.append({**meta,'public_text':body,'draft_text':draft_text})
     challenge_keys.append({**meta,'correct_action':mp[k],'draft_action':mp[action],'draft_is_correct':condition=='correct','draft_origin':'preauthored_fixed_challenge_not_natural_P0','single_error_mechanism':None if condition=='correct' else f['error_mechanisms'][int(changed)],'reason':reason,'public_sha256':sha(body),'draft_sha256':sha(draft_text),'expert_review':'pending'})
  # Difference and leakage tests use document payloads, not model results.
  base=docs(f,'base');changed=docs(f,'decisive_change');irr=docs(f,'irrelevant');missing=docs(f,'missing')
  assert [j for j in range(9) if base[j]!=changed[j]]==[3]
  assert [j for j in range(9) if base[j]!=irr[j]]==[7]
  assert [j for j in range(9) if base[j]!=missing[j]]==[3]
  assert oracle(f['id'],None)==3
  assert docs(f,'paraphrase')[0]!=base[0] and docs(f,'paraphrase')[1]!=base[1] and docs(f,'paraphrase')[3]!=base[3] and docs(f,'paraphrase')[6]!=base[6]
  # Both candidate critical values occur as general reference values in some dossiers,
  # but the missing record never supplies the entity-to-value association.
  critical=missing[3]['text'];assert str(f['base']) not in critical and str(f['changed']) not in critical
  checks.append({'family_id':f['id'],'decisive_source_only':'S4','irrelevant_source_only':'S8','missing_source_only':'S4','four_substantive_paraphrases':True,'missing_association_removed':True,'base_key':mp[f['key_base']],'changed_key':mp[f['key_changed']],'pause_key':mp[3]})
 count=Counter(k['correct_action'] for k in keys)
 assert count==dict.fromkeys('ABCD',20),count
 assert len(items)==80 and len(challenge)==32 and len({i['item_id'] for i in items})==80
 assert max(x['memo_length_ratio'] for x in ratios)<1.4
 # Boundary tests for numerical rules and deterministic category alternatives.
 boundary=[('M05',5425,0),('M05',5424,1),('M07',47,1),('M07',48,0),('M07',50,0)]
 for fid,val,expected in boundary:assert oracle(fid,val)==expected
 for f in F:
  for value,expected in [(f['base'],f['key_base']),(f['changed'],f['key_changed']),(None,3)]:assert oracle(f['id'],value)==expected
 write('prompts/p0_items.json',items);write('keys/p0_keys.json',keys)
 write('prompts/challenge_items.json',challenge);write('keys/challenge_keys.json',challenge_keys)
 write('cases/factual_truth_tables.json',truth)
 write('cases/validation.json',{'passed':True,'author_checks_only':True,'p0_items':80,'challenge_drafts':32,'p0_answer_distribution':dict(count),'family_count':8,'case_states':checks,'p0_char_range':[min(lengths),max(lengths)],'max_memo_length_ratio':max(x['memo_length_ratio'] for x in ratios),'memo_ratios':ratios,'oracle_tests':len(boundary)+len(F)*3,'boundary_tests':boundary,'shortcut_accuracy':{'always_same_letter':.25,'always_follow_memo':.5,'always_pause':.2},'public_input_never_contains_keys':True,'expert_review':'pending','blind_review':'pending','limitations':['Same-family authored synthetic rules, external validity unestablished.','Missing association can sometimes leave reference candidate values elsewhere; values alone do not identify the missing association.','Automatic checks do not certify all semantic ambiguities or guarantee difficulty.','Eight development families only; no independent heldout family tested.']})
 print(json.dumps({'p0_items':80,'challenge_drafts':32,'answer_distribution':dict(count),'chars':[min(lengths),max(lengths)],'max_memo_ratio':max(x['memo_length_ratio'] for x in ratios)},ensure_ascii=False))
if __name__=='__main__':main()
