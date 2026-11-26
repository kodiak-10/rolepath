"""Internship workbench for the conversion-funnel practice (local, sign-in-free)."""
from .i18n import t as tr, label, table
import streamlit as st
from . import practice
from .cloud_settings import cloud_mode
from .db import connect, save_practice_attempt, latest_practice_attempt, recent_plan, tasks_for
from .ui import go_to

NEXT_STEP_TEXTS = {
    'recompute': '重新对照数据表逐环节计算转化率：转化率 = 下一环节人数 ÷ 上一环节人数，再比较两个渠道的差距。',
    'check_denominator': '核对计算口径：该环节转化率应使用相邻两环节人数相除，而不是除以最初访问量。',
    'hypothesis': '把原因改写成可检验的假设，例如「渠道 B 的短信验证码到达率低」，并说明用什么数据能证实或排除。',
    'design_test': '为假设设计一个对照验证：如分渠道对比验证码发送成功率日志，或小流量 A/B 实验。',
    'write_recap': '把本次结论整理成一页复盘，并尝试用 SQL 从事件明细复算漏斗，巩固取数口径。',
    'extend_window': '尝试更换时间窗口或增加渠道数据，检查结论是否稳定，再写进你的作品集。',
}


def practice_visible(parsed, page=None):
    if cloud_mode():
        return False
    if practice.applies_to(parsed):
        return True
    conn = connect()
    try:
        return latest_practice_attempt(conn, practice.PRACTICE_ID) is not None
    finally:
        conn.close()


def _feedback_points(fb):
    strengths, fixes = [], []
    if fb['step_ok']:
        strengths.append(tr('环节定位正确：渠道 B 在「点击注册 → 完成手机验证」的流失明显高于渠道 A。'))
    else:
        fixes.append(tr('环节定位有误：请逐环节计算转化率，找出渠道 B 与渠道 A 差距最大的一步。'))
    for channel, ok, value in (('B', fb['rate_b_ok'], practice.TARGET_RATE_B), ('A', fb['rate_a_ok'], practice.TARGET_RATE_A)):
        if ok:
            strengths.append(tr('渠道 {0} 该环节转化率计算正确（{1}%）。', channel, f'{value:g}'))
        else:
            fixes.append(tr('渠道 {0} 转化率与参考值（{1}%）不符，请核对计算口径。', channel, f'{value:g}'))
    if fb['cause_ok'] and fb['cause_specific']:
        strengths.append(tr('原因假设具体、可检验。'))
    elif not fb['cause_ok']:
        fixes.append(tr('原因说明不足 20 字，请写成完整的可检验假设。'))
    else:
        fixes.append(tr('假设还不够具体：请落到验证码发送、到达或输入体验等可观测环节。'))
    if fb['verification_ok'] and fb['verification_specific']:
        strengths.append(tr('验证方法可执行。'))
    elif not fb['verification_ok']:
        fixes.append(tr('验证方法不足 20 字，请说明用什么数据或实验来检验假设。'))
    else:
        fixes.append(tr('验证方法缺少可操作手段：例如分渠道对比短信发送成功率日志，或小流量 A/B 实验。'))
    return strengths, fixes


def _render_feedback(attempt):
    fb = attempt['feedback']
    with st.container(border=True, key='rp_feedback'):
        st.markdown(tr('**导师反馈（规则点评，非 AI 生成）**'))
        st.metric(tr('本次得分'), f"{fb['score']} / 100")
        strengths, fixes = _feedback_points(fb)
        if strengths:
            st.markdown(tr('**做得好的地方**'))
            for line in strengths:
                st.write('· ' + line)
        if fixes:
            st.markdown(tr('**需要修正**'))
            for line in fixes:
                st.write('· ' + line)
        st.markdown(tr('**下一步建议**'))
        for code in fb['next_steps']:
            st.write('· ' + label(NEXT_STEP_TEXTS[code]))
        with st.expander(tr('查看本次提交')):
            sub = attempt['submission']
            st.write(tr('环节：') + label(sub['step_label']))
            st.write(tr('渠道 B 转化率：{0}% · 渠道 A 转化率：{1}%', sub['rate_b'], sub['rate_a']))
            st.write(tr('可能原因：') + sub['cause'])
            st.write(tr('验证方法：') + sub['verification'])
        st.caption(tr('提交时间：{0}', attempt['created_at']))


def render_workbench():
    st.subheader(tr('实习工作台 · 转化漏斗分析'))
    st.caption(tr('教学演示：导师、任务与数据均为模拟，不代表真实企业或真实用户数据。'))
    conn = connect()
    try:
        attempt = latest_practice_attempt(conn, practice.PRACTICE_ID)
        mentor, desk = st.columns([5, 7], gap='large')
        with mentor:
            with st.container(border=True, key='rp_mentor'):
                st.markdown(tr('**导师任务**'))
                st.write(tr('你是增长团队的数据分析实习生。请对比两个获客渠道近一周的注册漏斗，找出渠道 B 相对渠道 A 流失异常严重的环节，计算该环节两个渠道的转化率，并提出可能原因与验证方法。'))
                st.caption(tr('交付要求：定位一个环节；给出两个转化率数字；把原因写成可检验的假设；给出至少一种验证方法。'))
                plan_conn = connect()
                try:
                    plan = recent_plan(plan_conn)
                    plan_tasks = tasks_for(plan_conn, plan['id']) if plan else []
                finally:
                    plan_conn.close()
                pending = [t for t in plan_tasks if t['status'] == '待完成']
                if pending:
                    st.caption(tr('来自当前计划：{0}（{1} 截止）', pending[0]['title'], pending[0]['due']))
        with desk:
            st.markdown(tr('**练习数据 · 近一周注册漏斗（模拟数据）**'))
            st.dataframe(table(practice.data_rows()), hide_index=True, use_container_width=True)
            st.caption(tr('口径提示：环节转化率 = 下一环节人数 ÷ 上一环节人数 × 100%。请逐环节自行计算，不要除以最初访问量。'))
            # Plain widgets (not st.form) so an unsubmitted draft survives page switches.
            step = st.selectbox(tr('渠道 B 流失异常严重的环节'), list(range(len(practice.STEPS))),
                                format_func=lambda i: label(practice.STEPS[i]), key='practice_step')
            rate_col_b, rate_col_a = st.columns(2)
            rate_b = rate_col_b.number_input(tr('该环节渠道 B 转化率（%）'), min_value=0.0, max_value=100.0, value=0.0, step=0.1, key='practice_rate_b')
            rate_a = rate_col_a.number_input(tr('该环节渠道 A 转化率（%）'), min_value=0.0, max_value=100.0, value=0.0, step=0.1, key='practice_rate_a')
            cause = st.text_area(tr('可能原因（写成可检验的假设）'), max_chars=1000, key='practice_cause')
            verification = st.text_area(tr('验证方法（如何证实或排除假设）'), max_chars=1000, key='practice_verification')
            submitted = st.button(tr('提交分析结论'), type='primary', key='practice_submit')
            if submitted:
                if not cause.strip() or not verification.strip():
                    st.error(tr('请填写可能原因和验证方法后再提交。'))
                else:
                    submission = dict(step=step, step_label=practice.STEPS[step], rate_b=float(rate_b), rate_a=float(rate_a),
                                      cause=cause.strip(), verification=verification.strip())
                    feedback = practice.grade(submission)
                    save_practice_attempt(conn, practice.PRACTICE_ID, submission, feedback)
                    st.rerun()
            if attempt:
                _render_feedback(attempt)
                st.caption(tr('重新提交会保存为新的练习记录。'))
            else:
                st.info(tr('提交后这里会显示导师反馈。'))
            st.button(tr('返回学习计划 →'), on_click=go_to, args=('学习计划',), key='practice_back')
    finally:
        conn.close()


def render_practice_entry(plan_items=None):
    pending = [t for t in (plan_items or []) if t['status'] == '待完成'][:2]
    with st.container(border=True, key='rp_plan_practice'):
        st.markdown(tr('**岗位练习 · 转化漏斗分析**'))
        st.write(tr('以数据分析实习生身份完成一个模拟导师任务：对比渠道注册漏斗，定位流失环节并提交分析结论，获得规则点评。'))
        if pending:
            st.markdown(tr('**当前应做**'))
            opened = False
            for t in pending:
                left, right = st.columns([5, 1.7])
                with left:
                    st.markdown(f"**{t['title']}**")
                    st.caption(tr('{0} 截止 · {1} 分钟 · {2}', t['due'], t['minutes'], label(t['kind'])))
                with right:
                    if t['skill'] == '运营指标' and not opened:
                        st.button(tr('进入实习工作台 →'), key='practice_open', on_click=go_to, args=('实习工作台',), use_container_width=True)
                        opened = True
            if len(pending) > 1:
                st.caption(tr('做完之后：') + pending[1]['title'])
        else:
            st.button(tr('进入实习工作台 →'), key='practice_open', on_click=go_to, args=('实习工作台',), use_container_width=True)
        attempt = _latest_attempt()
        if attempt:
            _record_body(attempt)


def _latest_attempt():
    conn = connect()
    try:
        return latest_practice_attempt(conn, practice.PRACTICE_ID)
    finally:
        conn.close()


def _record_body(attempt):
    fb = attempt['feedback']
    st.markdown(tr('**岗位练习记录 · 转化漏斗分析**'))
    st.write(tr('最近提交：{0} · 得分 {1}/100', attempt['created_at'], fb['score']))
    st.write(tr('下一步建议：') + label(NEXT_STEP_TEXTS[fb['next_steps'][0]]))
    st.button(tr('继续练习 →'), on_click=go_to, args=('实习工作台',), key='practice_resume')


def render_practice_record():
    attempt = _latest_attempt()
    if not attempt:
        return
    with st.container(border=True, key='rp_practice_record'):
        _record_body(attempt)


def render_feedback_page():
    attempt = _latest_attempt()
    if not attempt:
        st.info(tr('还没有练习提交。完成一次岗位实操后，这里会显示评分依据与下一步。'))
        st.button(tr('去岗位实操 →'), type='primary', on_click=go_to, args=('岗位实操',), key='feedback_go')
        return
    _render_feedback(attempt)
    back, resume = st.columns(2)
    back.button(tr('返回学习计划 →'), type='primary', on_click=go_to, args=('学习计划',), key='feedback_back', use_container_width=True)
    resume.button(tr('继续练习 →'), on_click=go_to, args=('实习工作台',), key='feedback_resume', use_container_width=True)