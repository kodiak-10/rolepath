"""Student-facing workspace presentation; account data stays in existing stores."""
from .i18n import t as tr, label, table, formatter
from html import escape
import json
import streamlit as st
from .cloud_settings import cloud_mode, managed_ai, render_model_settings
from .db import connect, recent_plan, tasks_for, study_stats
from .jd import parse_jd

def apply_style():
    from pathlib import Path
    st.markdown('<style>'+Path(__file__).with_name('ui.css').read_text()+'</style>', unsafe_allow_html=True)

def go_to(page):
    st.session_state.page = page

def render_header():
    with st.container(key='rp_header'):
        brand, ask, account = st.columns([4, 1.15, 1.4])
        with brand:
            st.markdown('<div class="rp-brand"><span>◈</span>RolePath</div><div class="rp-sub">YOUR NEXT CHAPTER</div>', unsafe_allow_html=True)
        with ask:
            if st.button(tr('问一问'), type='primary', icon=':material/chat_bubble_outline:', key='global_note_chat', use_container_width=True):
                from .note_chat_ui import open_note_chat
                open_note_chat(st.session_state.get('jd_result'))
        with account:
            with st.popover(tr('账户与设置'), icon=':material/person_outline:', use_container_width=True):
                from .i18n import render_language_picker
                render_language_picker(compact=True)
                st.markdown(tr('**我的账户**'))
                if cloud_mode():
                    st.caption(st.session_state.get('_account_email', '个人账户'))
                    st.caption(tr('学习记录保存在你的账户中。'))
                    st.button(tr('使用额度') if managed_ai() else tr('AI 服务设置'), on_click=go_to, args=('AI 设置',), use_container_width=True)
                    if st.button(tr('退出登录'), key='account_logout'):
                        from .browser_session import logout
                        logout()
                        st.rerun()
                else:
                    st.caption(tr('本机个人空间'))
                    mode = st.selectbox(tr('资料查找方式'), ['关键词查找', '语义查找'], index=1 if st.session_state.get('_retriever_mode') == 'dense' else 0, format_func=formatter(), key='ui_d5d532d1eaaa')
                    st.session_state['_retriever_mode'] = 'dense' if mode == '语义查找' else 'lexical'
        st.write('')

def select_role(role):
    st.session_state['_jd_draft'] = role['demo_jd']
    st.session_state.jd_text = role['demo_jd']
    st.session_state.jd_result = parse_jd(role['demo_jd'])
    go_to('岗位分析')

def restore_plan(plan):
    meta = json.loads(plan['meta'])
    text = meta.get('jd', '')
    st.session_state['_jd_draft'] = text
    st.session_state.jd_text = text
    st.session_state.jd_result = meta.get('parsed') or parse_jd(text)
    st.session_state['_selected_plan_id'] = plan['id']
    go_to('学习任务')

def render_home(roles):
    con = connect()
    try:
        plan = recent_plan(con)
        tasks = tasks_for(con, plan['id']) if plan else []
        stats = study_stats(con, plan['id']) if plan else {'streak': 0, 'week_minutes': 0}
    finally:
        con.close()
    st.markdown(tr('<section class="rp-hero"><div class="rp-orbit" aria-hidden="true"></div>\n    <div class="eyebrow">从好奇开始 · 向目标前进</div><h1>你的下一步，<br>从这里变清晰。</h1>\n    <p>探索感兴趣的工作，拆解真实岗位要求。<br>把想去的方向，变成今天可以完成的一小步。</p></section>'), unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.button(tr('分析我的目标岗位 →'), type='primary', use_container_width=True, on_click=go_to, args=('岗位分析',))
    b.button(tr('继续学习 →') if plan else tr('制定学习计划 →'), use_container_width=True, on_click=restore_plan if plan else go_to, args=(dict(plan),) if plan else ('学习计划',))
    c.button(tr('整理我的笔记 →'), use_container_width=True, on_click=go_to, args=('学习笔记',))
    st.write('')
    a, b, c = st.columns(3)
    completed = sum((t['status'] == '已完成' for t in tasks))
    a.metric(tr('本周已记录'), tr('{0} 分钟', stats['week_minutes']))
    b.metric(tr('连续学习'), tr('{0} 天', stats['streak']))
    c.metric(tr('当前计划完成'), f'{completed} / {len(tasks)}')
    if plan:
        with st.container(border=True):
            st.markdown(tr('**正在准备**'))
            st.write(plan['target'])
            st.progress(completed / len(tasks) if tasks else 0, text=tr('按你记录的任务完成情况统计'))
    else:
        st.caption(tr('从零开始也没关系。分析一份岗位描述后，就可以制定自己的第一份计划。'))
    st.write('')
    st.subheader(tr('还没想好方向？先了解真实工作'))
    st.caption(tr('下面是三个入门示例，你也可以上传任意岗位描述。示例不代表实时招聘。'))
    for i, (col, role) in enumerate(zip(st.columns(len(roles)), roles)):
        with col, st.container(border=True):
            st.markdown(f"""<div class="rp-kicker">0{i + 1} / {escape(label(role['kind']))}</div><div class="rp-title">{escape(label(role['name']))}</div><p class="rp-desc">{escape(label(role['description']))}</p>""", unsafe_allow_html=True)
            st.markdown(''.join((f'<span class="rp-chip">{escape(label(skill))}</span>' for skill in role['skills'][:4])), unsafe_allow_html=True)
            st.button(tr('了解这个方向 ↗'), key='select_' + role['id'], on_click=select_role, args=(role,), use_container_width=True)
