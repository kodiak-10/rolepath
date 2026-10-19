"""Conservative, inspectable JD baseline. Not an LLM or a hiring predictor."""
from __future__ import annotations
import re
from .catalog import SKILL_ALIASES

_SENTENCES = re.compile(r"[^；;\n。，,]+")
_BONUS = re.compile(r"(优先|加分|更佳|plus|bonus)", re.IGNORECASE)
_HARD = [
    ("到岗时间", re.compile(r"(?:每周|一周)\s*(?:至少|不少于|需到岗|到岗|可实习|可到岗)?\s*[1-7]\s*(?:天|日)(?:及以上)?")),
    ("实习时长", re.compile(r"(?:至少|不少于|连续)?\s*(?:实习)?\s*\d+\s*(?:个)?月(?:以上)?(?:优先)?")),
    ("学历或年级", re.compile(r"(?:本科(?:及以上)?|硕士(?:优先)?|研究生|大[一二三四]|\d{4}\s*届)")),
    ("工作地点", re.compile(r"(?:Base|工作地点|地点)\s*[：:]\s*[^\n。]+", re.I)),
]

def _has_alias(text: str, alias: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9_ ]+", alias):
        # Reject matches within longer English words; SQL in MySQL still matches via its own alias.
        return re.search(r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])", text, re.IGNORECASE) is not None
    return alias.casefold() in text.casefold()

def source_units(text):
    # Preserve comma-separated context and every original requirement, including unknown skills.
    return [part.strip() for part in re.split(r'[\n；;。]+', text) if part.strip()]


def review_sources(text, requirements):
    return [dict(number=i+1, text=unit, skills=list(dict.fromkeys(
        r['skill'] for r in requirements if any(e in unit or unit in e for e in r.get('evidences', [r['evidence']])))))
        for i, unit in enumerate(source_units(text))]


def extract_skills(text: str) -> list[dict]:
    found = {}
    bonus_section = False
    for unit in source_units(text):
        if re.match(r'^\s*(?:加分项?|优先条件|加分条件)\s*[：:]?\s*$', unit):
            bonus_section = True
        elif re.match(r'^\s*(?:你会做|希望你|任职要求|职位要求|岗位职责|工作职责)\s*[：:]?', unit):
            bonus_section = False
        # Inline headings apply too, without requiring a colon.
        if re.match(r'^\s*加分项\s*[：:]', unit):
            bonus_section = True
        for fragment in _SENTENCES.findall(unit):
            sentence = fragment.strip(' \t\r-*•0123456789、.：:')
            if not sentence:
                continue
            for skill, aliases in SKILL_ALIASES.items():
                if not any(_has_alias(sentence, alias) for alias in aliases):
                    continue
                bonus = bonus_section or bool(_BONUS.search(sentence))
                emphasized = any(word in sentence for word in ('必须', '精通', '核心要求', '最看重'))
                priority = '加分项' if bonus else '常规要求'
                if skill not in found:
                    found[skill] = dict(skill=skill, priority=priority, evidence=unit,
                        evidences=[unit], detail=sentence, importance='原文明示重点' if emphasized else '未标注',
                        parser='关键词初筛')
                else:
                    row = found[skill]
                    if unit not in row['evidences']:
                        row['evidences'].append(unit)
                    if sentence not in row['detail']:
                        row['detail'] += '；' + sentence
                    if not bonus:
                        row['priority'] = '常规要求'
                        row['evidence'] = unit
                    if emphasized:
                        row['importance'] = '原文明示重点'
    return list(found.values())

def parse_jd(text: str) -> dict:
    if not text.strip():
        raise ValueError("JD 不能为空")
    requirements = extract_skills(text)
    hard = []
    for category, pat in _HARD:
        for match in pat.finditer(text):
            hard.append({"category": category, "text": match.group(0), "start": match.start()})
    return {"requirements": requirements, "source_review": review_sources(text, requirements), "constraints": hard, "unmapped_warning": "未识别的能力要求需要人工核查；规则模式不具备完整语义理解。", "mode": "规则关键词初筛（不完整）", "raw": text}
