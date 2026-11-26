"""Persistent companion Goudan: a floating puppy tutor chat over the current page."""
import json
import streamlit as st
from .i18n import t as tr, language
from .db import connect, recent_plan, tasks_for, latest_practice_attempt
from .llm import is_configured, tutor_answer
from .note_chat_ui import render_note_chat
from . import practice
from .practice_ui import NEXT_STEP_TEXTS

QUICK = {
    '我的空间': ['这个岗位做什么？', '我第一次实习，怎么开始？'],
    '看岗位': ['这些要求里先准备哪个？', '这个岗位做什么？'],
    '准备学习': ['我今天先做哪项？', '这周时间怎么安排？'],
    '岗位实操': ['这张表怎么读？', '给我一个提示'],
    '查看反馈': ['解释我的评分和下一步', '这周时间怎么安排？'],
}


def _context(parsed, page):
    parts = ['当前页面：' + page]
    if parsed:
        role = (parsed.get('orientation') or {}).get('role_name') or parsed['raw'].splitlines()[0][:60]
        parts.append('岗位：' + role)
        parts.append('JD 能力要求：' + '、'.join(r['skill'] for r in parsed.get('requirements', [])))
    conn = connect()
    try:
        plan = recent_plan(conn)
        if plan:
            tasks = tasks_for(conn, plan['id'])
            parts.append('计划任务：' + '；'.join(f"{t['due']} {t['title']}（{t['minutes']}分钟，{t['status']}）" for t in tasks[:8]))
            pending = [t for t in tasks if t['status'] == '待完成']
            if pending:
                parts.append('当前应做：' + pending[0]['title'])
        attempt = latest_practice_attempt(conn, practice.PRACTICE_ID)
    finally:
        conn.close()
    if page == '岗位实操' or attempt:
        parts.append('练习数据（模拟）：' + json.dumps(practice.data_rows(), ensure_ascii=False))
        parts.append('环节列表：' + '；'.join(practice.STEPS))
        parts.append('口径：环节转化率 = 下一环节人数 ÷ 上一环节人数 × 100%')
    if attempt:
        parts.append('最近提交：' + json.dumps(attempt['submission'], ensure_ascii=False))
        parts.append('规则反馈：' + json.dumps(attempt['feedback'], ensure_ascii=False))
        parts.append('下一步建议：' + '；'.join(NEXT_STEP_TEXTS[c] for c in attempt['feedback']['next_steps']))
    return '\n'.join(parts)


def render_doll(parsed=None):
    page = st.session_state.get('page', '我的空间')
    is_open = st.session_state.get('_doll_open', False)
    with st.container(key='rp_doll'):
        if st.button(tr('狗蛋助手'), key='doll_toggle'):
            st.session_state['_doll_open'] = not is_open
            st.rerun()
    if not is_open:
        return
    # Desktop: reserve independent space so data and the answer form stay visible.
    st.markdown('<style>@media(min-width:1000px){[data-testid="stMainBlockContainer"]{max-width:none;margin-right:414px}}</style>', unsafe_allow_html=True)
    configured = is_configured()
    with st.container(key='rp_doll_panel'):
        title, close = st.columns([5, 1.2])
        title.markdown(tr('**狗蛋 · 实习导师助手**'))
        if close.button(tr('收起'), key='doll_close', use_container_width=True):
            st.session_state['_doll_open'] = False
            st.rerun()
        quicks = list(QUICK.get(page, QUICK['我的空间']))
        conn = connect()
        try:
            has_attempt = latest_practice_attempt(conn, practice.PRACTICE_ID) is not None
        finally:
            conn.close()
        if page in ('岗位实操', '查看反馈') and has_attempt and '解释我的评分和下一步' not in quicks:
            quicks.append('解释我的评分和下一步')
        picked = None
        qcols = st.columns(len(quicks))
        for col, q in zip(qcols, quicks):
            if col.button(tr(q), key='doll_q_' + q, use_container_width=True, disabled=not configured):
                picked = tr(q)
        render_note_chat(
            parsed, picked, configured,
            lambda question, history: tutor_answer(question, _context(parsed, page), history, language()),
        )
