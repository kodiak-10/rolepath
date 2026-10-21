"""Student-facing workspace presentation; account data stays in existing stores."""
from html import escape
import json
import streamlit as st
from .cloud_settings import cloud_mode, render_model_settings
from .db import connect, recent_plan, tasks_for, study_stats
from .jd import parse_jd


def apply_style():
    st.markdown('''<style>
    :root {--rp-ink:#172d30;--rp-teal:#126859;--rp-line:#dce7e2}
    .stApp {background:#f6f8f5;color:var(--rp-ink)}
    .block-container {max-width:1180px;padding:2.5rem 2rem 2rem}
    h1,h2,h3 {letter-spacing:-.035em;color:var(--rp-ink)!important}
    [data-testid="stHeader"] {background:transparent}
    [data-testid="stToolbar"] {display:none}
    .rp-brand {font-weight:800;font-size:25px;letter-spacing:-1px;margin:0}
    .rp-brand span {color:var(--rp-teal);margin-right:8px}
    .rp-sub {color:#74837f;font-size:12px;letter-spacing:2px;margin-top:4px}
    [data-testid="stRadio"]>div[role="radiogroup"] {gap:5px;flex-wrap:wrap;background:#eaf0eb;padding:6px;border-radius:14px}
    [data-testid="stRadio"] label {border-radius:10px;padding:8px 12px;margin:0!important;transition:background .18s}
    [data-testid="stRadio"] label:has(input:checked) {background:white;box-shadow:0 2px 7px #16372c12}
    [data-testid="stRadio"] label>div:first-child {display:none}
    [data-testid="stRadio"] label p {font-size:14px!important}
    .stButton button,[data-testid="stPopover"] button {border-radius:10px;border-color:var(--rp-line);min-height:42px;transition:transform .18s,box-shadow .18s;background:#fff;color:var(--rp-ink)}
    .stButton button:hover {border-color:#126859;color:#126859;transform:translateY(-2px);box-shadow:0 5px 12px #183b2810}
    .stButton button[kind="primary"] {background:#126859;border-color:#126859;color:white}
    .stButton button:focus-visible {outline:3px solid #6ba896;outline-offset:3px}
    [data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:16px!important}
    [data-testid="stMetric"] {background:white;border:1px solid var(--rp-line);padding:20px;border-radius:16px}
    [data-testid="stMetricValue"] {color:var(--rp-teal)}
    [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {color:#172d30;background:#fff}
    [data-testid="stExpander"] {background:white;border-radius:14px}
    .rp-hero {position:relative;overflow:hidden;background:#143f38;border-radius:24px;padding:42px 44px;color:#fff;margin:8px 0 22px;min-height:240px}
    .rp-hero .eyebrow {color:#a8cdbb;font-size:12px;letter-spacing:3px;margin-bottom:18px}
    .rp-hero h1 {font-size:42px;line-height:1.3;color:#fff!important;margin:0 0 14px;position:relative;z-index:1;max-width:75%}
    .rp-hero p {color:#d2e5dc;max-width:67%;line-height:1.9;margin:0;position:relative;z-index:1}
    .rp-orbit {position:absolute;right:-50px;top:-90px;width:340px;height:340px;border:1px solid #76ad8b50;border-radius:50%;box-shadow:0 0 0 45px #76ad8b0d,0 0 0 90px #76ad8b0b}
    .rp-orbit:after {content:'✦';position:absolute;left:90px;top:180px;color:#d8e8a8;font-size:72px}
    .rp-kicker {font-size:12px;color:#568575;font-weight:700;letter-spacing:2px;margin-bottom:10px}
    .rp-title {font-size:21px;font-weight:750;margin:0 0 8px}
    .rp-desc {font-size:14px;color:#63756d;line-height:1.8;min-height:50px}
    .rp-chip {display:inline-block;background:#eaf1eb;color:#446458;border-radius:6px;font-size:12px;padding:4px 8px;margin:0 5px 7px 0}
    @media(max-width:700px){.block-container{padding:1.5rem 1rem}.rp-hero{padding:28px 22px;min-height:210px}.rp-hero h1{font-size:30px;max-width:100%}.rp-hero p{max-width:100%}.rp-orbit{opacity:.25}.rp-brand{font-size:22px}}
    @media(prefers-reduced-motion:reduce){.stButton button{transition:none}.stButton button:hover{transform:none}}
    </style>''', unsafe_allow_html=True)


def go_to(page):
    st.session_state.page = page


def render_header():
    brand, account = st.columns([5, 1.4])
    with brand:
        st.markdown('<div class="rp-brand"><span>◈</span>RolePath</div><div class="rp-sub">YOUR NEXT CHAPTER</div>', unsafe_allow_html=True)
    with account:
        with st.popover('账户与设置', use_container_width=True):
            st.markdown('**我的账户**')
            if cloud_mode():
                st.caption(st.session_state.get('_account_email', '个人账户'))
                st.caption('学习记录保存在你的账户中。')
                render_model_settings()
                if st.button('退出登录', key='account_logout'):
                    try:
                        st.session_state['_account_client'].auth.sign_out()
                    finally:
                        st.session_state.clear()
                    st.rerun()
            else:
                st.caption('本机个人空间')
                mode = st.selectbox('资料查找方式', ['关键词查找', '语义查找'], index=1 if st.session_state.get('_retriever_mode') == 'dense' else 0)
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
    go_to('学习任务')


def render_home(roles):
    con = connect()
    try:
        plan = recent_plan(con)
        tasks = tasks_for(con, plan['id']) if plan else []
        stats = study_stats(con, plan['id']) if plan else {'streak':0, 'week_minutes':0}
    finally:
        con.close()
    st.markdown('''<section class="rp-hero"><div class="rp-orbit" aria-hidden="true"></div>
    <div class="eyebrow">从好奇开始 · 向目标前进</div><h1>你的下一步，<br>从这里变清晰。</h1>
    <p>探索感兴趣的工作，拆解真实岗位要求。<br>把想去的方向，变成今天可以完成的一小步。</p></section>''', unsafe_allow_html=True)
    a,b,c = st.columns(3)
    a.button('分析我的目标岗位 →', type='primary', use_container_width=True, on_click=go_to, args=('岗位分析',))
    b.button('继续学习 →' if plan else '制定学习计划 →', use_container_width=True, on_click=restore_plan if plan else go_to, args=(dict(plan),) if plan else ('学习计划',))
    c.button('整理我的笔记 →', use_container_width=True, on_click=go_to, args=('学习笔记',))
    st.write('')
    a,b,c = st.columns(3)
    completed = sum(t['status']=='已完成' for t in tasks)
    a.metric('本周已记录', f"{stats['week_minutes']} 分钟")
    b.metric('连续学习', f"{stats['streak']} 天")
    c.metric('当前计划完成', f'{completed} / {len(tasks)}')
    if plan:
        with st.container(border=True):
            st.markdown('**正在准备**')
            st.write(plan['target'])
            st.progress(completed/len(tasks) if tasks else 0, text='按你记录的任务完成情况统计')
    else:
        st.caption('从零开始也没关系。分析一份岗位描述后，就可以制定自己的第一份计划。')
    st.write('')
    st.subheader('还没想好方向？先了解真实工作')
    st.caption('下面是三个入门示例，你也可以上传任意岗位描述。示例不代表实时招聘。')
    for i, (col, role) in enumerate(zip(st.columns(len(roles)), roles)):
        with col, st.container(border=True):
            st.markdown(f'<div class="rp-kicker">0{i+1} / {escape(role["kind"])}</div><div class="rp-title">{escape(role["name"])}</div><p class="rp-desc">{escape(role["description"])}</p>', unsafe_allow_html=True)
            st.markdown(''.join(f'<span class="rp-chip">{escape(skill)}</span>' for skill in role['skills'][:4]), unsafe_allow_html=True)
            st.button('了解这个方向 ↗', key='select_'+role['id'], on_click=select_role, args=(role,), use_container_width=True)
