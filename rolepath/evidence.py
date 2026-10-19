from __future__ import annotations
from .catalog import SKILL_ALIASES
from .jd import _has_alias
import re

def _negated_mention(text: str, skill: str) -> bool:
    # A conservative special case: do not treat “不会 SQL” as positive evidence.
    negatives = r"(?:不熟悉|不会|没学过|未学过|还没学过|不了解|没有使用过|没有|没做过|不懂|未接触)"
    return any(re.search(negatives + r"[^，。；\n]{0,9}" + re.escape(alias), text, re.IGNORECASE) for alias in SKILL_ALIASES.get(skill, [skill]))

def assess(requirements: list[dict], declared: list[str], notes: str) -> list[dict]:
    """Text mentions are never treated as a verified competency."""
    output = []
    for req in requirements:
        skill = req['skill']
        found_note = any(_has_alias(notes, word) for word in SKILL_ALIASES.get(skill, [skill])) and not _negated_mention(notes, skill)
        if found_note:
            status = "材料提及（待验证）"
        elif skill in declared:
            status = "个人自述（待验证）"
        else:
            status = "暂无证据"
        output.append({**req, "status": status, "material_mention": found_note, "self_reported": skill in declared})
    return output
