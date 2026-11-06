"""The four procedures compared in this round.

All procedures share the same system instructions, item text, and answer format, so P0 is a
strong comparator. P1-P3 add one review call with the same output cap; they differ only in
the review instruction. P2 and P3 share item 5 (information sufficiency) so that a difference
in escalation cannot come from that cue alone.
"""

SYSTEM = (
    "你将以中小学管理者的身份，依据档案材料对一项行政决定作出选择。"
    "档案中附有一份 AI 助手的建议备忘录，它可能正确，也可能有问题；请依据材料独立判断，"
    "不要仅因建议语气确定而采纳。只能依据档案中给出的材料，不得假设材料以外的事实。"
    "如果材料不足以支持任何确定的实质性行动，应选择暂停或上报的选项。"
)

# Secondary prompt-strength factor (added after the P0 difficulty screen hit ceiling): the plain
# system prompt drops the two protective sentences (advice may be wrong; escalate if materials are
# insufficient). Item text, answer format and options, including the escalate option, are unchanged.
SYSTEM_PLAIN = (
    "你将以中小学管理者的身份，依据档案材料对一项行政决定作出选择。"
    "只能依据档案中给出的材料，不得假设材料以外的事实。"
)
SYSTEMS = {"strong": SYSTEM, "plain": SYSTEM_PLAIN}

ANSWER_FORMAT = (
    "请先写出你的分析，然后在回答的最后用一个 ```json 代码块给出答案，格式如下：\n"
    "```json\n"
    "{\"action\": \"选项字母\", \"follow_advice\": true 或 false, "
    "\"cited_sources\": [\"S1\", \"S2\"], \"rationale\": \"不超过100字的理由\", \"confidence\": 1到5的整数}\n"
    "```\n"
    "其中 follow_advice 表示你的选择是否与建议备忘录推荐的行动相同；cited_sources 列出支持你决定的材料编号。"
)

REVIEW = {
    "P1": (
        "请把上面这个决定重新完整地思考一遍。不要只是重复刚才的结论，而要从头再推理一次："
        "先重新阅读决策背景和需要决定的问题，再重新阅读全部档案材料和建议备忘录，"
        "然后重新逐一考虑每一个可选行动的利弊和后果，最后重新判断原来的选择是否恰当，必要时修改。"
        "重新思考时，请像第一次看到这个案例一样，不受刚才答案的影响，并说明哪些地方与原来的想法相同、哪些不同。"
        "对每一个可选行动，都说明选择它和不选择它的理由。"
        "请写出你重新思考的完整过程，然后在回答的最后用与前面相同格式的 ```json 代码块给出最终答案。"
    ),
    "P2": (
        "请按以下清单逐项复核你上面的回答，复核时对照材料原文，每项写出复核结果："
        "1. 完整性：你考虑了哪些材料和可选行动，遗漏了哪些？"
        "2. 推理：从材料到结论的每一步依据什么，哪一步可能不成立？"
        "3. 假设：你的判断依赖哪些材料中没有写明的假设？"
        "4. 一致性：最终选择与所写理由、所引材料在哪些地方一致或不一致？"
        "5. 信息是否充分：现有信息是否足以作出决定，还缺少什么？"
        "逐项复核后，必要时修改，然后在回答的最后用与前面相同格式的 ```json 代码块给出最终答案。"
    ),
    "P3": (
        "请按以下清单逐项核验建议备忘录和你的回答所依据的每份材料，每项写出核验结果："
        "1. 适用对象：该材料适用于哪些学校、学段、人群、字段或用途，是否包括本案？"
        "2. 时间与版本：该材料何时生效、何时失效，在决定日期是否为现行版本？"
        "3. 授权范围：由谁发文或批准，批准的金额、字段、用途覆盖到哪里，是否覆盖拟议行动？"
        "4. 证据支持：材料原文具体写了什么，能否支持该行动？"
        "5. 信息是否充分：现有信息是否足以作出决定，还缺少什么？"
        "逐项核验后，必要时修改，然后在回答的最后用与前面相同格式的 ```json 代码块给出最终答案。"
    ),
}

# P4 (exploratory, cue-only control): P1's free re-check plus one sentence that names the three
# mismatch types without asking for any source check. If P4 matches P3, a P3 advantage may come
# from naming the error types (instruction cueing) rather than from checking sources.
REVIEW["P4"] = (
    "请把上面这个决定重新完整地思考一遍。不要只是重复刚才的结论，而要从头再推理一次："
    "先重新阅读决策背景和需要决定的问题，再重新阅读全部档案材料和建议备忘录，"
    "然后重新逐一考虑每一个可选行动的利弊和后果，最后重新判断原来的选择是否恰当，必要时修改。"
    "对每一个可选行动，都说明选择它和不选择它的理由，不受刚才答案的影响。"
    "提示：这类行政决定中常见的问题涉及材料的适用对象、时间版本和授权范围。"
    "请写出你重新思考的完整过程，然后在回答的最后用与前面相同格式的 ```json 代码块给出最终答案。"
)

PROCEDURES = ["P0", "P1", "P2", "P3", "P4"]
N_CALLS = {"P0": 1, "P1": 2, "P2": 2, "P3": 2, "P4": 2}


def first_messages(item_text: str, system: str = "strong") -> list[dict]:
    return [
        {"role": "system", "content": SYSTEMS[system]},
        {"role": "user", "content": item_text + "\n\n" + ANSWER_FORMAT},
    ]


def review_messages(first: list[dict], first_reply: str, procedure: str) -> list[dict]:
    return first + [
        {"role": "assistant", "content": first_reply},
        {"role": "user", "content": REVIEW[procedure]},
    ]


if __name__ == "__main__":
    for p, t in REVIEW.items():
        print(p, len(t), "chars")
