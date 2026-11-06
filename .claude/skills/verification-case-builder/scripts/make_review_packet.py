"""Build a Markdown review packet for independent domain reviewers.

Usage:
  python make_review_packet.py <folder> -o packet.md            # full packet with keys
  python make_review_packet.py <folder> -o blind.md --blind     # answer sheet without keys

Use the blind packet first (reviewers choose the action for every state without seeing the
key), then the full packet (reviewers judge realism, the key, irrelevant facts, and the pause
condition). Standard library only.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caselib as cl  # noqa: E402

STATE_ZH = {"base": "基础", "decisive_change": "关键事实变化", "irrelevant_change": "无关变化",
            "paraphrase": "改写", "missing": "关键材料缺失"}
ADVICE_ZH = {"aligned": "正确建议", "flawed": "错误建议"}


def sources_md(sources):
    return "\n".join(f"- **[{s['id']}] {s['title']}**：{s['text']}" for s in sources)


def full_family(fam):
    out = [f"## {fam['family_id']} {fam['title']}",
           f"领域：{fam['domain']}；错配类型：{fam['mismatch_type']}；难度：{fam['difficulty']}；"
           f"集合：{fam['split']}；审核状态：{fam['expert_review'].get('status')}", "",
           f"**背景**：{fam['context']}", "", f"**问题**：{fam['decision_question']}", "", "**选项**："]
    out += [f"- {k}. {v}" for k, v in sorted(fam["options"].items())]
    out += ["", "**基础材料**：", sources_md(cl.state_sources(fam, "base")), "",
            f"**关键事实**（{fam['decisive_fact']['source_id']}）：{fam['decisive_fact']['why_decisive']}",
            "**无关事实**：" + "；".join(f"{f['source_id']}：{f['why_irrelevant']}" for f in fam["irrelevant_facts"]),
            f"**暂停／上报条件**：{fam['pause_condition']}", ""]
    for st in cl.STATES:
        sd = fam["states"][st]
        out.append(f"### 状态：{STATE_ZH[st]}（正确行动 {sd['key_action']}）")
        if st != "base":
            if st == "paraphrase":
                out.append("材料全部改写，内容不变：")
                out.append(sources_md(cl.state_sources(fam, st)))
            else:
                for e in sd.get("edits", []):
                    if e["op"] == "replace":
                        out.append(f"- 修改 {e['source_id']} 为：{e['text']}")
                    elif e["op"] == "remove":
                        out.append(f"- 删除 {e['source_id']}")
                    elif e["op"] == "reorder":
                        out.append(f"- 材料顺序改为：{'、'.join(e['order'])}")
                    elif e["op"] == "add":
                        out.append(f"- 新增 {e['source']['id']}：{e['source']['text']}")
        out.append(f"- **答案依据**：{sd['answer_basis']}")
        out.append(f"- 必须引用：{'、'.join(sd['required_sources'])}；允许引用：{'、'.join(sd['permitted_sources'])}")
        for adv in cl.ADVICE:
            a = sd["advice"][adv]
            out.append(f"- **{ADVICE_ZH[adv]}**（建议 {a['recommends']}）：")
            out.append("  > " + a["text"].replace("\n", "\n  > "))
            if adv == "flawed":
                out.append(f"  - 误用方式：{a['how_misapplied']}")
        out.append("")
    out += ["### 审核意见（请填写）",
            "| 项目 | 评价 | 意见 |", "|---|---|---|",
            "| 情境真实性（1-5） | | |",
            "| 各状态正确行动是否成立（同意／不同意，并写出你的答案） | | |",
            "| 无关事实是否确实不影响决定 | | |",
            "| 暂停／上报条件是否符合实际上报渠道 | | |",
            "| 错误建议是否像真实的 AI 建议（不过分明显） | | |",
            "| 其他问题 | | |", ""]
    return "\n".join(out)


def blind_sheet(fams, seed):
    rng = random.Random(seed)
    entries = [(fam, st) for fam in fams for st in cl.STATES]
    rng.shuffle(entries)
    out = ["# 案例独立作答表（不含答案）", "",
           "请只依据每个案例给出的材料，选择你作为学校管理者会采取的行动，并写出依据的材料编号。"
           "本表不显示任何 AI 建议。", ""]
    mapping = []
    for n, (fam, st) in enumerate(entries, 1):
        view = cl.state_view(fam, st)
        out += [f"## 第 {n} 题", f"**背景**：{view['context']}", "", f"**问题**：{view['decision_question']}", "",
                sources_md(view["sources"]), "", "**选项**："]
        out += [f"- {k}. {v}" for k, v in sorted(view["options"].items())]
        out += ["", "你的选择：____　依据材料编号：____　说明：________", ""]
        mapping.append(f"| {n} | {fam['family_id']} | {st} | {fam['states'][st]['key_action']} |")
    key = ["# 作答表对照（研究者保存，勿发给审核人）", "", "| 题号 | 家族 | 状态 | 正确行动 |", "|---|---|---|---|", *mapping]
    return "\n".join(out), "\n".join(key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--seed", type=int, default=20261105)
    args = ap.parse_args()
    fams = cl.load_dir(args.folder)
    out = Path(args.out)
    if args.blind:
        sheet, key = blind_sheet(fams, args.seed)
        out.write_text(sheet, encoding="utf-8")
        key_path = out.with_name(out.stem + "_KEY.md")
        key_path.write_text(key, encoding="utf-8")
        print(f"Wrote {out} and {key_path} ({len(fams)} families)")
    else:
        body = ["# 案例审核材料（含答案）", "",
                "以下案例由 AI 起草，尚未经独立领域人员核定。请逐项评价并填写审核意见。", ""]
        body += [full_family(f) for f in fams]
        out.write_text("\n".join(body), encoding="utf-8")
        print(f"Wrote {out} ({len(fams)} families)")


if __name__ == "__main__":
    main()
