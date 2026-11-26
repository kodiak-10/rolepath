"""Conversion-funnel practice: simulated mentor task and deterministic rule feedback.

All data is fictional teaching material; feedback never calls a model.
"""
from __future__ import annotations

PRACTICE_ID = 'funnel_v1'

STAGES = ['落地页访问', '点击注册', '完成手机验证', '填写资料', '注册成功']
CHANNELS = {
    '渠道 A · 应用商店': [8000, 3600, 2700, 2160, 1900],
    '渠道 B · 信息流广告': [6000, 3000, 900, 720, 630],
}
STEPS = [f'{STAGES[i]} → {STAGES[i + 1]}' for i in range(len(STAGES) - 1)]
TARGET_STEP = 1


def step_rates(counts):
    return [counts[i + 1] / counts[i] * 100 for i in range(len(counts) - 1)]


TARGET_RATE_B = step_rates(CHANNELS['渠道 B · 信息流广告'])[TARGET_STEP]
TARGET_RATE_A = step_rates(CHANNELS['渠道 A · 应用商店'])[TARGET_STEP]
RATE_TOLERANCE = 2.0

_CAUSE_HINTS = ('验证码', '短信', '手机号', '运营商', '到达', '延迟', '加载', '输入', '验证')
_TEST_HINTS = ('a/b', 'ab实验', 'ab 实验', '实验', '对照', '埋点', '日志', '访谈', '灰度', '分渠道', '成功率')


def applies_to(parsed):
    return bool(parsed) and any(r['skill'] == '运营指标' for r in parsed.get('requirements', []))


def data_rows():
    rows = [dict(渠道=channel, **dict(zip(STAGES, counts))) for channel, counts in CHANNELS.items()]
    totals = [sum(counts[i] for counts in CHANNELS.values()) for i in range(len(STAGES))]
    rows.append(dict(渠道='合计', **dict(zip(STAGES, totals))))
    return rows


def grade(submission):
    """Score a submission against the simulated data; return flags and next-step codes."""
    cause = submission.get('cause', '').strip()
    verification = submission.get('verification', '').strip()
    step_ok = submission.get('step') == TARGET_STEP
    rate_b_ok = abs(float(submission.get('rate_b', 0)) - TARGET_RATE_B) <= RATE_TOLERANCE
    rate_a_ok = abs(float(submission.get('rate_a', 0)) - TARGET_RATE_A) <= RATE_TOLERANCE
    cause_ok = len(cause) >= 20
    cause_specific = any(word in cause for word in _CAUSE_HINTS)
    verification_ok = len(verification) >= 20
    verification_specific = any(word in verification.casefold() for word in _TEST_HINTS)
    score = (40 * step_ok + 15 * rate_b_ok + 15 * rate_a_ok
             + 10 * cause_ok + 5 * cause_specific + 10 * verification_ok + 5 * verification_specific)
    next_steps = []
    if not step_ok:
        next_steps.append('recompute')
    if not (rate_b_ok and rate_a_ok):
        next_steps.append('check_denominator')
    if not (cause_ok and cause_specific):
        next_steps.append('hypothesis')
    if not (verification_ok and verification_specific):
        next_steps.append('design_test')
    next_steps.append('write_recap')
    if score == 100:
        next_steps.append('extend_window')
    return dict(score=score, step_ok=step_ok, rate_b_ok=rate_b_ok, rate_a_ok=rate_a_ok,
                cause_ok=cause_ok, cause_specific=cause_specific,
                verification_ok=verification_ok, verification_specific=verification_specific,
                next_steps=next_steps)