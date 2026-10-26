"""RolePath V0.1 — local, single-user exploratory MVP."""
from __future__ import annotations
from rolepath.i18n import t as tr, label, table, formatter
import os
import json
import hashlib
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from rolepath.cloud_settings import cloud_mode, managed_ai, render_model_settings
from rolepath.credits import run_ai_task, task_notice
from rolepath.catalog import ALL_SKILLS, load_resources, load_roles
from rolepath.db import connect, recent_plan, all_plans, save_plan, set_task_status, tasks_for, log_study, study_stats
from rolepath.evidence import assess
from rolepath.ingest import read_upload
from rolepath.image_text import UPLOAD_TYPES
from rolepath.knowledge import pages_from_upload, save_document, get_documents, get_chunks, delete_document, search_lexical, search_dense
from rolepath.jd import parse_jd
from rolepath.llm import grounded_answer, answer_from_document, is_configured, parse_jd_with_llm
from rolepath.planner import plan_tasks
from rolepath.retrieval import build_retriever
from rolepath.matching import coverage, reviewed_domestic, learning_requirements
from rolepath.notes_ui import render_notes
if not cloud_mode():
    load_dotenv()
from rolepath.ui import apply_style, render_header, go_to, render_home
st.set_page_config(page_title='RolePath · Your next chapter', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
apply_style()
from rolepath.i18n import init_language
init_language()
if cloud_mode():
    from rolepath.cloud_auth import require_login
    require_login()
render_header()
ROLES = load_roles()
RESOURCES = load_resources()

@st.cache_resource(show_spinner=False)
def get_retriever(mode: str, catalog_version: str):
    return build_retriever(RESOURCES, mode)
retriever_name = st.session_state.get('_retriever_mode', 'lexical')
try:
    retriever = get_retriever(retriever_name, hashlib.sha256(json.dumps(RESOURCES, ensure_ascii=False).encode()).hexdigest())
    retrieval_ok = True
except Exception as exc:
    retrieval_ok = False
    st.error(tr('学习资源暂时无法加载，请稍后刷新。'))
    st.stop()
if 'jd_text' not in st.session_state:
    st.session_state.jd_text = ''
if 'jd_result' not in st.session_state:
    st.session_state.jd_result = None
if 'last_plan_id' not in st.session_state:
    st.session_state.last_plan_id = None
PAGES = ['我的空间', '岗位分析', '课程与题目', '学习计划', '学习任务', '学习笔记', '历史记录']
if st.session_state.get('page') == '资料问答':
    st.session_state['page'] = '学习笔记'
if st.session_state.get('page') == 'AI 设置':
    PAGES.append('AI 设置')
st.session_state.setdefault('page', PAGES[0])
st.session_state.setdefault('_jd_draft', st.session_state.jd_text)
st.session_state['_prefer_domestic'] = True
st.session_state.jd_text = st.session_state['_jd_draft']
page_labels = {value: tr('使用额度') if value == 'AI 设置' and managed_ai() else label(value) for value in PAGES}
page = st.radio(tr('工作空间导航'), PAGES, key='page', horizontal=True, label_visibility='collapsed', format_func=page_labels.get)
st.write('')
if page == '我的空间':
    render_home(ROLES)
if page == '岗位分析':
    st.subheader(tr('把目标 JD 变成可检查的能力要求'))
    st.write(tr('粘贴 JD 或上传 TXT / MD / PDF。照片请先在学习笔记的照片助手中转录并核对，再粘贴到这里。') if cloud_mode() else tr('直接粘贴 JD，或上传 TXT / MD / PDF、PNG / JPG / HEIC 图片。推荐使用真实岗位，解析结果会保留原文证据。'))
    uploaded_jd = st.file_uploader(tr('上传岗位 JD（可选）'), type=(['txt', 'md', 'pdf'] if cloud_mode() else UPLOAD_TYPES), key='jd_upload')
    st.text_area(tr('岗位 JD 原文'), key='jd_text', on_change=lambda: st.session_state.update(_jd_draft=st.session_state.jd_text), height=210, placeholder=tr('粘贴岗位名称、职责、任职要求、优先条件和实习时间…'))
    parse_mode = st.selectbox(tr('解析方式'), ['关键词初筛（不完整，无需 API）', 'LLM 结构化抽取（需 API Key）'], index=1 if is_configured() else 0, format_func=(lambda value: tr('AI 深度分析') if value.startswith('LLM') else tr('关键词预览')) if managed_ai() else formatter(), key='ui_ace9d4ab6562')
    if parse_mode.startswith('LLM'):
        task_notice()
    else:
        st.caption(tr('关键词预览不调用 AI，也不消耗使用次数；它不能代替完整岗位分析。'))
    if st.button(tr('解析岗位要求'), type='primary', key='do_parse'):
        try:
            jd_text = read_upload(uploaded_jd) if uploaded_jd else st.session_state.jd_text
            if not jd_text.strip():
                st.session_state.jd_result = None
                st.warning(tr('请粘贴 JD 或上传文件。'))
            elif parse_mode.startswith('LLM'):
                if not is_configured():
                    raise ValueError('LLM 未配置：请填写 API Key 和模型名称，或选择不完整的关键词初筛。')
                st.session_state.jd_result = run_ai_task('jd', lambda: parse_jd_with_llm(jd_text, with_orientation=True))
            else:
                st.session_state.jd_result = parse_jd(jd_text)
        except Exception as exc:
            st.session_state.jd_result = None
            st.error(tr('无法解析该 JD：{0}', exc))
    parsed = st.session_state.jd_result
    if parsed:
        if parsed.get('orientation'):
            st.write(parsed['orientation']['overview'])
            st.caption(tr('已同时生成岗位入门建议、基础概念与面试准备，请在「课程与题目」查看。'))
        next_a, next_b = st.columns(2)
        next_a.button(tr('查看匹配课程 →'), on_click=go_to, args=('课程与题目',), use_container_width=True)
        next_b.button(tr('制定学习计划 →'), on_click=go_to, args=('学习计划',), use_container_width=True)
        st.caption(tr('解析方式：') + parsed['mode'])
        if parsed['mode'].startswith('规则'):
            st.warning(tr('下面只是词库命中，不是完整岗位分析，也不是重要性排名。完整拆解需要配置模型；请逐条核对下面的 JD 原文。'))
        reqs = parsed['requirements']
        if reqs:
            st.dataframe(table([{'能力要求': x['skill'], '具体要求': x.get('detail', x['evidence']), '要求类别': x['priority'], '明确强调': x.get('importance', '未标注'), '对应原文': x['evidence']} for x in reqs]), hide_index=True, use_container_width=True)
        else:
            st.warning(tr('未发现可识别的技能，请核查 JD 原文；规则词库并不覆盖所有岗位要求，可在下方补充。'))
        with st.expander(tr('逐条核对 JD：包含未识别内容'), expanded=True):
            for row in parsed.get('source_review', []):
                st.write(f"{row['number']}. {row['text']}")
                st.caption(tr('已关联：') + '、'.join(row['skills']) if row['skills'] else tr('尚未关联能力：请核对是否包含遗漏的职责、技能或条件。'))
            st.caption(tr('关联到一个标签不代表整条要求已经完整分析。'))
        if parsed['constraints']:
            st.markdown(tr('**可能的非技能条件（需人工确认）**'))
            st.dataframe(table([{'类别': c['category'], '原文片段': c['text']} for c in parsed['constraints']]), hide_index=True, use_container_width=True)
        st.info(tr('学历、毕业年份、地点与实习时间请先自行确认；学习计划不能替代这些条件。'))
        with st.expander(tr('补充漏识别的岗位要求')):
            with st.form('add_requirement'):
                skill = st.text_input(tr('技能或业务要求'), max_chars=50, key='ui_1eb7d8260480')
                evidence = st.text_input(tr('粘贴对应 JD 原文片段'), key='ui_0e995c648d5c')
                priority = st.selectbox(tr('要求类别'), ['常规要求', '加分项'], format_func=formatter(), key='ui_a7cb2d6c0fbe')
                add = st.form_submit_button(tr('补充要求'))
            if add:
                if not skill.strip() or not evidence.strip() or evidence.strip() not in parsed['raw']:
                    st.error(tr('请填写要求名称，并引用当前 JD 中真实存在的原文。'))
                elif any((r['skill'] == skill.strip() for r in parsed['requirements'])):
                    st.warning(tr('该要求已存在。'))
                else:
                    parsed['requirements'].append(dict(skill=skill.strip(), evidence=evidence.strip(), priority=priority, parser='人工补充'))
                    st.rerun()
if page == '课程与题目':
    st.subheader(tr('按 JD 选择课程与有来源的题目'))
    prefer_domestic = True
    parsed = st.session_state.jd_result
    if not parsed:
        st.info(tr('先载入或解析一份 JD。'))
    else:
        guide = parsed.get('orientation')
        if not guide:
            st.write(tr('JD 写得宽泛也可以准备：让 AI 解释岗位工作、基础概念、建议先学什么，以及可能的面试问题。'))
            task_notice()
            if st.button(tr('生成岗位入门建议'), type='primary', key='make_orientation'):
                try:
                    st.session_state.jd_result = run_ai_task('jd', lambda: parse_jd_with_llm(parsed['raw'], with_orientation=True))
                    st.rerun()
                except Exception as exc:
                    st.error(tr('岗位建议生成失败：{0}', exc))
        else:
            st.markdown(tr('**这个岗位做什么**'))
            st.write(guide['overview'])
            st.caption(tr('以下是 AI 根据岗位背景提出的准备建议，不是企业明示要求，也不是实际面试题预测。'))
            with st.expander(tr('先理解这些概念')):
                for concept in guide['concepts']:
                    st.markdown(f"**{concept['name']}**")
                    st.write(concept['explanation'])
            with st.expander(tr('面试准备 · AI 模拟题（非企业真题）')):
                for i, question in enumerate(guide['interview'], 1):
                    st.write(f"{i}. {question['question']}")
                    st.caption(question['assesses'])
            st.markdown(tr('**按顺序学习与练习**'))
        for group in coverage(learning_requirements(parsed), retriever, prefer_domestic):
            r = group['requirement']
            with st.expander(r['skill'] + ' · ' + r['priority']):
                st.write((tr('建议原因：') if r.get('origin') == 'guidance' else tr('JD 原文：')) + r['evidence'])
                if r.get('origin') == 'guidance':
                    st.write(tr('学习目标：') + r['detail'])
                if not group['courses']:
                    st.warning(tr('当前没有核验过的匹配课程，不自动安排无来源学习任务。'))
                visible_courses = group['courses']
                if prefer_domestic:
                    domestic_courses = [h for h in group['courses'] if reviewed_domestic(h.resource)]
                    if domestic_courses:
                        visible_courses = domestic_courses
                    elif group['courses']:
                        st.caption(tr('这项能力暂无已核查的国内来源，以下为补充参考。'))
                for hit in visible_courses[:3]:
                    c = hit.resource
                    st.markdown(f"**[{c['title']}]({c['url']})**")
                    st.write(tr('对应学习内容：') + c.get('focus', {}).get(r['skill'], c['description']))
                    st.caption(tr('发布方：{0} · 发布：{1} · 本次学习预算约 {2} 分钟（含练习，非整课时长）', c.get('creator', '官方资料/原发布方'), c.get('published', '见原站'), c.get('minutes_by_skill', {}).get(r['skill'], c['minutes'])))
                    for chapter in c.get('chapters', {}).get(r['skill'], []):
                        st.markdown(tr('[{0}]({1}) · {2} 分钟', chapter['title'], chapter['url'], chapter['seconds'] // 60))
                    st.caption(c.get('quality_basis', '按资源目录技能标签匹配') + '；' + c.get('freshness_note', '内容时效以原站为准'))
                    st.caption(tr('核查：') + c.get('checked_at', '原有资源，本轮未核查') + ' · ' + c.get('verification', ''))
                    st.caption(tr('访问说明：') + c.get('access_note', tr('补充参考来源，国内可达性未实测。')))
                if not group['questions']:
                    st.caption(tr('暂无核查过的对应题目。计划可安排成果练习，但不会标成企业真题。'))
                for q in group['questions']:
                    st.markdown(tr('练习：[{0}]({1})', q['title'], q['url']))
                    st.caption(q['source_type'] + ' · ' + q['source'] + ' · ' + q['published'])
                    st.write(q['summary'])
                    st.caption(tr('来源核查：{0} · {1}', q.get('checked_at', '未标注'), q.get('access_note', '以原站权限为准。')))
        st.info(tr('题目区分平台练习、企业题库或历史套卷、用户回忆面经。企业归属以平台或作者标注为准，未获企业单独确认；旧题不代表当前考试。'))
if page == '学习计划':
    st.subheader(tr('能力证据与个性化学习计划'))
    parsed = st.session_state.jd_result
    if not parsed or not learning_requirements(parsed):
        st.info(tr('先去「我的空间」载入一个演示 JD，或在「岗位分析」中提交真实 JD。'))
    else:
        include_guidance = st.checkbox(tr('将岗位入门建议加入计划（不是企业硬性要求）'), value=True, key='include_guidance') if parsed.get('orientation') else False
        requirements = learning_requirements(parsed, include_guidance)
        col_a, col_b = st.columns([3, 2])
        with col_a:
            claimed = st.multiselect(tr('你认为自己接触过哪些技能？（仅作自述，不视为已掌握）'), list(dict.fromkeys(ALL_SKILLS + [r['skill'] for r in requirements])), key='ui_eb570ab6ba05')
            notes = st.text_area(tr('项目经历、学习成果或作品说明（可选）'), height=130, placeholder=tr('例：我做过RAG知识库问答项目，记录了检索结果；尚未做系统评测。'), key='ui_bf3afc2595b1')
            upload_evidence = st.file_uploader(tr('上传自己的项目文档或学习笔记（可选）'), type=(['txt', 'md', 'pdf'] if cloud_mode() else UPLOAD_TYPES), key='profile_upload')
            if upload_evidence:
                try:
                    notes = notes + '\n' + read_upload(upload_evidence)[:18000]
                    st.caption(tr('材料已在本地读取；提及某技能不等于能力已通过验证。'))
                except Exception as exc:
                    st.error(tr('读取个人资料失败：{0}', exc))
        with col_b:
            hours = st.slider(tr('每周可用学习时间（小时）'), min_value=1, max_value=30, value=8, key='ui_ef3a7187fdff')
            days = st.slider(tr('准备周期（天）'), min_value=3, max_value=90, value=14, key='ui_d3906eea5fd9')
            st.caption(tr('规划器会遵循总时间预算。固定练习任务只是候选计划，不代表标准化课时。'))
        evaluated = assess(requirements, claimed, notes)
        st.markdown(tr('**当前能力证据（未经技能测验）**'))
        st.dataframe(table([{'技能': a['skill'], 'JD要求': a['priority'], '状态': a['status']} for a in evaluated]), hide_index=True, use_container_width=True)
        if st.button(tr('生成并保存学习路径'), type='primary', key='make_plan'):
            tasks, summary = plan_tasks(evaluated, retriever, hours, days, prefer_domestic=st.session_state['_prefer_domestic'])
            if not tasks:
                st.error(tr('没有可安排的任务：请检查课程缺口或增加时间预算。未覆盖原有计划。'))
            else:
                conn = connect()
                try:
                    pid = save_plan(conn, parsed['raw'].splitlines()[0][:100], tasks, {'hours_per_week': hours, 'days': days, 'jd': parsed['raw'], 'summary': summary, 'retrieval': retriever_name, 'parsed': parsed})
                    st.session_state.last_plan_id = pid
                    st.session_state['_selected_plan_id'] = pid
                finally:
                    conn.close()
                st.success(tr('已保存 {0} 个任务。', len(tasks)))
                st.button(tr('开始学习 →'), on_click=go_to, args=('学习任务',))
        conn = connect()
        try:
            latest = recent_plan(conn)
            plan_items = tasks_for(conn, latest['id']) if latest else []
        finally:
            conn.close()
        if latest:
            meta = __import__('json').loads(latest['meta'])
            summary = meta.get('summary', {})
            a, b, c = st.columns(3)
            a.metric(tr('计划总预算'), tr('{0:.1f}小时', summary.get('capacity_minutes', 0) / 60))
            b.metric(tr('已安排任务'), len(plan_items))
            c.metric(tr('待安排技能'), len(summary.get('unscheduled_skills', [])))
            st.caption(tr('这里展示最近一次保存的计划；修改 JD 或时间后，请重新生成计划。每个学习预算是本次章节学习与练习时间，不是学完整套课程。'))
            if summary.get('missing_resources'):
                st.warning(tr('课程缺口（未编造资源）：') + '、'.join(summary['missing_resources']))
            if summary.get('unscheduled_skills'):
                st.warning(tr('当前计划未安排：') + '、'.join(summary['unscheduled_skills']))
            st.dataframe(table([{'预计日期': t['due'], '技能': t['skill'], '类型': t['kind'], '任务': t['title'], '分钟': t['minutes'], '学习链接': t['resource_url'] or '无'} for t in plan_items]), hide_index=True, use_container_width=True)
            sessions = [{'日期': ss['date'], '任务': t['title'], '分钟': ss['minutes']} for t in plan_items for ss in t.get('sessions', [])]
            if sessions:
                with st.expander(tr('每日学习安排（较长任务分天完成）')):
                    st.dataframe(table(sessions), hide_index=True)
if page == '学习任务':
    st.subheader(tr('执行任务 · 保存进度'))
    conn = connect()
    try:
        plans = all_plans(conn)
        selected_id = st.session_state.get('_selected_plan_id')
        latest = next((p for p in plans if p['id'] == selected_id), plans[0] if plans else None)
        if not latest:
            st.info(tr('目前还没有学习计划。去「学习计划」创建。'))
        else:
            tasks = tasks_for(conn, latest['id'])
            stats = study_stats(conn, latest['id'])
            a, b, c = st.columns(3)
            a.metric(tr('连续学习'), tr('{0} 天', stats['streak']))
            b.metric(tr('本周记录'), tr('{0} 分钟', stats['week_minutes']))
            c.metric(tr('累计学习日'), stats['days'])
            if stats['days'] >= 7:
                st.success(tr('已积累 7 个学习日，坚持记录，也记得复习与休息。'))
            elif stats['days'] >= 1:
                st.success(tr('已迈出第一步！下一次记录可以写下遇到的一个问题。'))
            if tasks:
                with st.form('daily_study'):
                    tid = st.selectbox(tr('今天学习的任务'), [t['id'] for t in tasks], format_func=lambda v: next((t['title'] for t in tasks if t['id'] == v)), key='ui_22cf5c357e92')
                    mins = st.number_input(tr('今天学习分钟数'), min_value=1, max_value=1440, value=30, step=5, key='ui_28faa2ec3c4e')
                    reflection = st.text_area(tr('今天学到了什么、遇到了什么问题？'), max_chars=3000, key='ui_b902ca1d71c4')
                    logged = st.form_submit_button(tr('保存今日打卡'))
                if logged:
                    try:
                        log_study(conn, tid, int(mins), reflection)
                        st.rerun()
                    except ValueError as exc:
                        st.error(label(str(exc)))
                st.caption(tr('同一任务同一天重复保存会更新记录，不重复累计。打卡与完成任务都是自报，不代表能力已验证。'))
                if stats['logs']:
                    with st.expander(tr('学习记录')):
                        st.dataframe(table([{'日期': r['day'], '任务': r['title'], '分钟': r['minutes'], '记录': r['reflection']} for r in stats['logs']]), hide_index=True)
            completed = sum((t['status'] == '已完成' for t in tasks))
            st.progress(completed / len(tasks) if tasks else 0, text=tr('任务记录完成：{0}/{1}（不代表能力已验证）', completed, len(tasks)))
            for t in tasks:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"**{t['title']}**")
                        st.caption(tr('{0} · {1}分钟 · {2} · {3}', t['due'], t['minutes'], t['kind'], t['priority']))
                        st.write(tr('提交/自查标准：') + t['acceptance'])
                        if t.get('matching_reason'):
                            st.caption(t['matching_reason'])
                        for chapter in t.get('chapters', []):
                            st.markdown(tr('观看分集：[{0}]({1})', chapter['title'], chapter['url']))
                        if t.get('question'):
                            q = t['question']
                            st.markdown(tr('题目来源：[{0}]({1})', q['title'], q['url']))
                            st.caption(q['source_type'] + ' · ' + q['source'])
                        if t['resource_url']:
                            st.markdown(tr('学习资源：[打开 {0}]({1})', t['resource_title'], t['resource_url']))
                    with c2:
                        checked = st.checkbox(tr('已完成'), value=t['status'] == '已完成', key=f"task_{t['id']}")
                        if checked != (t['status'] == '已完成'):
                            set_task_status(conn, t['id'], '已完成' if checked else '待完成')
                            st.rerun()
            st.info(tr('本版“完成”仅代表用户自报。自动评测练习作品和动态重排属于下一版本。'))
    finally:
        conn.close()
if page == '学习笔记':
    render_notes(st.session_state.jd_result)
if page == 'AI 设置':
    if not managed_ai():
        st.subheader(tr('连接你的 AI 服务'))
        st.write(tr('由你自己的百炼账户提供智能分析。学习记录和 AI 配置分开保存。'))
    if cloud_mode():
        render_model_settings()
    else:
        st.info(tr('本机版本从本地环境配置读取 AI 服务。'))
if page == '历史记录':
    from rolepath.history_ui import render_history
    render_history()
from rolepath.note_chat_ui import render_open_note_chat
render_open_note_chat(st.session_state.jd_result)
st.divider()
st.caption(tr('RolePath · 让每一次学习，都靠近想去的方向。\u3000｜\u3000学习建议请结合原始资料核对。'))
