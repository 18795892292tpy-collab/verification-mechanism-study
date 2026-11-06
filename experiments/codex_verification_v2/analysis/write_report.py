#!/usr/bin/env python3
"""Write a Chinese v2 report only from verified, terminal real experiment records."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

from plot_results import (ROOT, PROCS, load_completed_data, read, require,
                          resource_totals, sha256, verify_unchanged)


def pct(n, d):
    return f'{n}/{d}（{100*n/d:.1f}%）' if d else 'NA（分母为 0）'


def pp(value):
    return 'NA' if value is None else f'{100*value:+.2f} 个百分点'


def span(value):
    return 'NA' if value is None else f'[{100*value[0]:+.2f}, {100*value[1]:+.2f}]'


def usage_cell(value, field):
    n, total = value[field + '_known'], value['attempts']
    if value[field] is None:
        return f'NA（可知 {n}/{total}；缺失 {total-n} attempts）'
    formatted = f"{value[field]:,.1f}" if field == 'seconds' else f"{value[field]:,}"
    return f'{formatted}（可知 {n}/{total}；缺失 {total-n}' + ('）' if value[field+'_complete'] else '；仅已知部分）')


def build_report(summary, rows, attempts):
    byproc = summary['procedures']
    states = Counter(r['status'] for r in rows)
    blocked = states.get('not_run_first_failed', 0)
    failed = len(rows) - summary['complete_tasks'] - blocked
    runtime = read(ROOT / 'protocol/runtime_identity.json')
    frozen = read(ROOT / 'protocol/frozen.json')
    concurrency = summary['presentation_concurrency']
    extra_chars = read(ROOT / 'protocol/prompts.json')['extra_chars']
    first = [r for r in rows if r['procedure'] == 'P0']
    first_present = [r for r in first if r['state'] != 'missing']
    errors = [r for r in first_present if r['status'] == 'complete' and r['correct'] == 0]
    unobserved = sum(r['status'] != 'complete' for r in first_present)
    lines = [
        '# Codex 来源与条款核验 v2：固定 800 任务开发实验', '',
        f"生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}。评价类型：`simulation_only`。", '',
        '本报告从已保存的真实 CLI 作答记录重新核验并统计；合成的是案例与规则，结果不是模拟填入值。'
        '全部 800 个计划任务已有终态，终态不等同于成功完成。没有真人参与，也没有外部教育行政专家验证。', '',
        '## 研究问题与执行前偏离', '',
        '在封闭的虚构学校规则任务中，考察增加条款触发条件核验的 P7，相对来源核验 P3 和近等长通用复核 P8 的正确率差异。'
        '主要估计量为证据在场且建议错误（`present_flawed`）的 I78：条款条件家族的 P7−P8 家族均值，减去材料适用性家族的相应均值。'
        'I73（P7−P3 的相同交互）是次要估计量。', '',
        '相对原 Issue 3 / `approved_plan.md` 中额外筛查、选题和追加预算建议，本批在任何被试模型作答前采用 '
        '`protocol/EXECUTION_AMENDMENT.md`：固定 8 家族、80 题、2 次重复、5 程序，共 800 个计划任务。'
        '160 个 P0 同时用于描述难度和提供共享首轮；不另做 160 次筛查，不使用 960/1120 调用方案。'
        '不根据 P0 或复核结果删题、换家族或扩大预算；出现天花板也完成原固定矩阵。'
        '这属于执行前偏离，不应表述为完全执行原 Issue 3 方案或独立保留集验证。', '',
        '### 执行中并发修订（与上述执行前方案修订分开披露）', '',
        f"依据 `protocol/CONCURRENCY_AMENDMENT_2026-11-07.json`，用户执行中两次要求提速后，"
        f"在 {concurrency['prior_terminal_tasks']} 个任务已有终态（其中 {concurrency['prior_complete_tasks']} 个成功完成）时，"
        f"原调度器安全停止；剩余 {concurrency['remaining_tasks_at_amendment']} 个计划任务的最大并发配置由 "
        f"{concurrency['from_workers']} 直接调整为 {concurrency['to_workers']}。6 并发从未实际运行，"
        '该事实同时由修订说明及保存的调度器启动日志核对。并发数是调度上限，不表示全过程始终有同样数量任务同时运行。', '',
        f"修订保存时间（UTC）：{concurrency['created_utc']}。原调度器退出码为 {concurrency['prior_runner_exit_code']}，"
        '修订记录说明这是有意向调度器父进程发送 SIGINT；当时运行中的任务已结束并封存后才保存切换快照。'
        '已封存 final 未重新抽样，原冻结科学输入、模型与推理配置、提示、冻结任务清单与计划顺序、重试上限和评分器保持原样；实际完成先后可随并发变化。', '',
        '这项变化是执行中操作性偏离，不能写成执行前已经固定的并发设置。'
        '执行由原冻结驱动与非冻结的 `harness/run_concurrency_override.py` 分段完成，'
        '追加修订、应用证据和启动日志的哈希一并收入图表与报告来源清单。', '',
        '## 方法与可追溯性', '',
        '8 个构造家族分为 4 个材料适用性家族和 4 个条款条件家族；每家族 5 状态 × 2 建议方向。'
        '每题 2 次首轮重复；每一 item/repeat 组的 P1/P3/P7/P8 使用同一个 P0 原文及其哈希，复核之间不共享上下文。'
        'P0 为基础决定，P1 为自由复核，P3 为来源核验，P7 在 P3 上增加条款条件核验，P8 在 P3 上增加近等长通用复核。'
        f"P7/P8 新增指令正文（不含分隔换行）分别为 {extra_chars['P7']}、{extra_chars['P8']} 个字符，"
        '仅近似匹配长度；不能据此声称相同隐藏推理计算量。', '',
        f"请求配置：{runtime['model_requested']} / {runtime['effort_requested']}，CLI {runtime['cli_version']}，"
        f"主机 {runtime['host']}；冻结时间 {frozen['created_utc']}。底层权重快照、采样 seed 和温度均未知，"
        '不能宣称与桌面应用具有完全相同的系统提示或内部配置。', '',
        '正确性按固定规则答案与最终 `action` 是否一致判定，不使用 LLM 裁判，不将理由或引用质量冒充正确率。'
        '参考答案由执行前的规则、真值表和排除说明固定；匿名内部题库审查属于同模型家族检查，'
        '其相关误判和共同盲点不能由匿名化消除，也不构成独立专家效度验证。', '',
        '正确率的分母包含全部计划任务；解析失败、技术失败和因首轮失败而未启动的复核记为 0。'
        '错误答案或已有 final 的解析失败不重新抽样，只有无 final 的技术失败按冻结规则有限重试。'
        '因此实际 CLI attempt 数可能不同于计划任务数。', '',
        '重复、状态变体与建议方向不是独立家族。统计单位为案例家族，每类型内等权；'
        '每类型仅 4 个构造家族，仅报告描述性点估计与观测家族范围，不报告确认性 p 值、置信区间或功效结论。', '',
        '## 执行与失败情况', '',
        f"计划 {len(rows)} 个任务，终态 {len(rows)} 个；成功完成 {summary['complete_tasks']} 个，"
        f'已执行但失败 {failed} 个，首轮失败导致复核未启动 {blocked} 个。'
        f"实际 CLI attempts 为 {len(attempts)}，记录到的独立会话 ID 为 {summary['unique_sessions']}。"
        f"完整成功配对组 {summary['complete_groups']}/{summary['planned_groups']}。", '',
        '| 终态 | 任务数 |', '|---|---:|']
    for status, count in sorted(states.items()):
        lines.append(f'| {status} | {count} |')
    lines += ['', '| 程序 | 计划 | 成功完成 | 非成功终态 | 实际 attempts |', '|---|---:|---:|---:|---:|']
    for p in PROCS:
        rr = [r for r in rows if r['procedure'] == p]
        lines.append(f"| {p} | {len(rr)} | {byproc[p]['complete']} | {len(rr)-byproc[p]['complete']} | {sum(r['attempts'] for r in rr)} |")
    lines += ['', '## 结果', '',
              '| 程序 | 全部题目正确 | present_flawed 正确 | 证据缺失时正确 | 修复自然首轮错误 | 正确首轮未被保留 |',
              '|---|---:|---:|---:|---:|---:|']
    for p in PROCS:
        v = byproc[p]
        repair = '不适用' if p == 'P0' else pct(v['repaired'], v['natural_first_errors'])
        damage = '不适用' if p == 'P0' else pct(v['damaged'], v['first_correct_present'])
        lines.append(f"| {p} | {pct(v['correct'],v['planned'])} | {pct(v['present_flawed_correct'],v['present_flawed_n'])} | "
                     f"{pct(v['missing_correct'],v['missing_n'])} | {repair} | {damage} |")
    lines += ['', '条件纠错仅以证据在场且成功完成、但答错的 P0 为分母。分母为 0 时必须记为 NA，不是 0%。'
              '正确首轮未被保留包括复核改错以及复核失败；后者不等于观察到模型主动改错。', '',
              '### P0 难度诊断（不用于选择或停止）', '',
              f'证据在场的自然首轮错误：{len(errors)} 个，来自 {len({r["family_id"] for r in errors})} 个家族；'
              f'另有 {unobserved} 个证据在场 P0 未成功完成，不能当作可解析的自然错误。', '',
              '| 类型 | present_flawed 正确/计划 | 成功完成 | 自然错误 | 有自然错误的家族数 | aligned 且在场正确/计划 | 缺证据正确/计划 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for kind, v in summary['difficulty_diagnostic']['by_type'].items():
        lines.append(f"| {kind} | {pct(v['present_flawed_correct'],v['present_flawed_planned'])} | "
                     f"{v['present_flawed_completed']} | {v['present_flawed_natural_errors']} | {len(v['error_families'])} | "
                     f"{pct(v['aligned_present_correct'],v['aligned_present_planned'])} | {pct(v['missing_correct'],v['missing_planned'])} |")
    if summary['difficulty_diagnostic']['complete_P0_present_ceiling']:
        lines += ['', '全部证据在场 P0 均成功且正确，观察到本题库上的首轮天花板。没有可供修复的自然首轮错误，'
                  '条件纠错率为 NA；正确率交互仍可计算，但不能据此证明核验机制优越、无效或等价。']
    elif not errors:
        lines += ['', '未观察到成功完成的证据在场 P0 自然错误；由于有未成功任务，不能把这称为完整首轮天花板。'
                  '条件纠错率为 NA，失败仍保留在全部计划正确率分母中。']
    else:
        lines += ['', '本批存在可供条件纠错分析的自然首轮错误；纠错与改错结果仍限于这些构造家族。']
    lines += ['', '### present_flawed 家族对比', '',
              '| 家族 | 类型 | P7−P8 | P7−P3 |', '|---|---|---:|---:|']
    c78 = summary['primary_interactions']['I78']; c73 = summary['secondary_interaction_I73']
    f73 = {f['family_id']: f for f in c73['families']}
    for f in c78['families']:
        lines.append(f"| {f['family_id']} | {f['error_type']} | {pp(f['difference'])} | {pp(f73[f['family_id']]['difference'])} |")
    lines += ['', '| 对比 | 材料家族均值 | 材料家族范围（百分点） | 条款家族均值 | 条款家族范围（百分点） |',
              '|---|---:|---:|---:|---:|']
    for name, c in summary['within_type_contrasts'].items():
        lines.append(f"| {name} | {pp(c['type_mean_difference']['material'])} | {span(c['type_family_difference_range']['material'])} | "
                     f"{pp(c['type_mean_difference']['rule'])} | {span(c['type_family_difference_range']['rule'])} |")
    lines += ['', f"主要 I78 = {pp(c78['estimate'])}；次要 I73 = {pp(c73['estimate'])}。"
              '范围只是观测家族差值的最小值与最大值，不是置信区间，也不是交互估计量的不确定性区间。', '',
              '### 完整配对敏感性与其他层', '',
              '| 分析 | I78 | I73 |', '|---|---:|---:|',
              f"| present_flawed，全计划分母（主要） | {pp(c78['estimate'])} | {pp(c73['estimate'])} |",
              f"| present_flawed，仅完整配对 | {pp(summary['complete_pair_sensitivity']['I78']['estimate'])} | "
              f"{pp(summary['complete_pair_sensitivity']['I73']['estimate'])} |"]
    for stratum, cc in summary['secondary_interactions'].items():
        lines.append(f"| {stratum}，全计划分母 | {pp(cc['I78']['estimate'])} | {pp(cc['I73']['estimate'])} |")
    lines += ['', '完整配对分别要求 P0、P7 和相应比较程序成功完成，属于敏感性分析，不能替换包含失败的主要分母。'
              '`all`、`aligned` 和 `missing` 为预设次要层；`aligned` 按评分器定义含其所有证据状态。', '']
    for name, cc in summary['complete_pair_sensitivity'].items():
        ns = cc['available_families_by_type']
        pair_count = sum(f['paired_groups'] for f in cc['families'])
        lines.append(f"{name} 完整配对：保留 {pair_count} 组，材料 {ns['material']} 个可用家族、条款 {ns['rule']} 个可用家族。")
    lines += ['', '## 实际资源日志', '',
              '| 程序 | 实际 attempts | 输入 tokens | 输出 tokens | attempt 时长合计（秒） |',
              '|---|---:|---:|---:|---:|']
    for p in PROCS + ['合计']:
        totals = resource_totals(attempts, None if p == '合计' else p)
        lines.append(f"| {p} | {totals['attempts']} | {usage_cell(totals,'input_tokens')} | "
                     f"{usage_cell(totals,'output_tokens')} | {usage_cell(totals,'seconds')} |")
    times = []
    for a in attempts:
        try:
            start, end = (datetime.fromisoformat(a[k]) for k in ['started_utc', 'finished_utc'])
            if start.tzinfo is not None and end.tzinfo is not None and end >= start:
                times.append((start, end))
        except (KeyError, ValueError, TypeError):
            pass
    wall = ((max(end for _,end in times)-min(start for start,_ in times)).total_seconds()
            if len(times) == len(attempts) and times else None)
    lines += ['', '首个实际 attempt 开始至最后一个结束的墙钟跨度：' +
              ('NA（时间日志不足）' if wall is None else f'{wall/60:.1f} 分钟（包含运行间隔与暂停）') + '。'
              '并发 attempt 时长之和不是墙钟时间。P0 只计自己的调用一次，复核行仅计复核本身，包含合法技术重试。', '',
              '资源与时延汇总混合了 3 并发和 12 并发两个阶段，且切换发生在已完成 667 项后；剩余任务并非随机抽取的性能对照组。'
              '时段、任务构成、服务端负载、排队与暂停均可能影响时延，不能从前后墙钟差异推断因果提速倍数，'
              '也不能将各程序在混合并发下的累计时长当作公平的速度或工作负担比较。token 计量仍按实际日志汇总，'
              '并发提速不等于单次模型推理变快或节省相同比例的计算与费用。', '',
              '账单核实费用：NA。没有已核实价格及收费账单，不从 token 数虚构成本。'
              '这里的 token 是 CLI 日志返回的计量，不是 FLOPs、隐藏推理算力或现金支出。'
              '起草题库、同模型家族匿名审查、工具开发、协调、图表审阅等管理开销完整用量未知，未计入被试任务合计；'
              '因此不能称为整个研究的全部资源消耗。缺失 usage 不当作 0，表中不完整部分只报告已知小计。', '',
              '## 解释边界与图表', '',
              '所有对比只描述本批 8 个构造家族。4 个家族/类型的设计无法支持总体优势、等价、独立机制隔离或现实教育政策效果的确认性结论。'
              '共同模型家族参与题库检查可能共享盲点；没有真人样本、真实校长/教师行为测量、外部专家效度验证或独立保留集。'
              'v1 和历史 DeepSeek 数据没有作为本报告统计输入。', '',
              '| 主张 | 本批可核查证据 | 可支持范围 |', '|---|---|---|',
              '| 共享首轮与不同复核上下文 | 原始 prompt、首轮哈希、会话与事件审计 | 本批记录完整性 |',
              f"| P0 任务正确率 | {pct(byproc['P0']['correct'],byproc['P0']['planned'])} | 当前构造题库的描述性表现 |",
              '| P7 的独特优势或等价 | 家族点估计和范围，没有确认性推断 | 不作机制或总体结论 |',
              '| 真人工作负担或教育效果 | 没有真人及外部效度数据 | 本研究不能回答 |', '',
              '图组：`fig1_design`（标为 planned 的设计示意）、`fig2_family_accuracy`（逐家族正确率）、'
              '`fig3_family_contrasts`（present_flawed 的 I78/I73 家族点与范围）、`fig4_resources`（实际 attempt 资源）。'
              '图形文件是否已生成以 `figures/figure_manifest.json` 为准；本报告不替代人工视觉审查。', '',
              '来源 SHA-256 清单见 `report/report_manifest.json`；图输出及其源哈希见 `figures/figure_manifest.json`。'
              '绘图方法及技能来源见 `FIGURE_PROVENANCE.md`。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        summary, rows, attempts, hashes = load_completed_data()
        text = build_report(summary, rows, attempts)
        if args.check_only:
            print(json.dumps({'ready': True, 'terminal_tasks': len(rows), 'report_characters': len(text)}))
            return 0
        out = ROOT / 'report'; out.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.report_', dir=out) as td:
            staged = Path(td) / 'DEV_REPORT.md'
            staged.write_text(text, encoding='utf-8')
            verify_unchanged(hashes)
            manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'phase': 'dev',
                        'planned_tasks': 800, 'terminal_tasks': len(rows), 'complete_tasks': summary['complete_tasks'],
                        'actual_cli_attempts': len(attempts), 'input_sha256': hashes,
                        'dispatch_concurrency': summary['presentation_concurrency'],
                        'output_sha256': {'DEV_REPORT.md': sha256(staged)}, 'results_source': 'verified saved real records'}
            staged.replace(out / 'DEV_REPORT.md')
            (out / 'report_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({'report': str(out / 'DEV_REPORT.md'), 'actual_attempts': len(attempts)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print('Refusing to write report: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
