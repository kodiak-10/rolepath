"""RolePath V0.1 — local, single-user exploratory MVP."""
from __future__ import annotations
import os
import json
import hashlib
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from rolepath.cloud_settings import cloud_mode, render_model_settings

from rolepath.catalog import ALL_SKILLS, load_resources, load_roles
from rolepath.db import connect, recent_plan, save_plan, set_task_status, tasks_for, log_study, study_stats
from rolepath.evidence import assess
from rolepath.ingest import read_upload
from rolepath.image_text import UPLOAD_TYPES
from rolepath.knowledge import (pages_from_upload, save_document, get_documents, get_chunks, delete_document, search_lexical, search_dense)
from rolepath.jd import parse_jd
from rolepath.llm import grounded_answer, answer_from_document, is_configured, parse_jd_with_llm
from rolepath.planner import plan_tasks
from rolepath.retrieval import build_retriever
from rolepath.matching import coverage
from rolepath.notes_ui import render_notes

if not cloud_mode():
    load_dotenv()
st.set_page_config(page_title='RolePath · 实习成长助手', page_icon='🧭', layout='wide')
if cloud_mode():
    from rolepath.cloud_auth import require_login
    require_login()

st.markdown('''<style>
.block-container {padding-top: 1.7rem; max-width: 1180px}
[data-testid="stMetric"] {border: 1px solid #e1e7eb; border-radius: 12px; padding: 12px}
div[data-testid="stAlert"] {border-radius: 10px}
</style>''', unsafe_allow_html=True)

ROLES = load_roles()
RESOURCES = load_resources()

@st.cache_resource(show_spinner='初始化检索器中…')
def get_retriever(mode: str, catalog_version: str):
    return build_retriever(RESOURCES, mode)

with st.sidebar:
    st.header('RolePath · V0.1')
    st.caption('你的个人学习空间 · 记录保存在云端账户' if cloud_mode() else '你的岗位准备与学习空间 · 资料保存在本机')
    st.divider()
    if cloud_mode():
        render_model_settings()
    st.write('**模型状态**')
    st.write('LLM：' + ('✅ API 已配置' if is_configured() else '◻ 未配置，使用规则解析'))
    with st.expander('高级设置'):
        retrieval_mode = st.radio('资料查找方式', (['关键词查找（快速）'] if cloud_mode() else ['关键词查找（快速）','语义查找（首次需加载模型）']), horizontal=False)
        st.caption('当前云端版本支持关键词查找，尚未启用语义查找。' if cloud_mode() else '关键词查找匹配文字；语义查找用于寻找意思相近的段落。')
    retriever_name = 'dense' if retrieval_mode.startswith('语义') else 'lexical'
    st.divider()
    st.caption('笔记、计划、打卡与分析记录按登录账户隔离。' if cloud_mode() else '当前没有账户与权限隔离，请仅在本机测试，不要直接公开部署或上传他人隐私资料。')

try:
    retriever = get_retriever(retriever_name, hashlib.sha256(json.dumps(RESOURCES, ensure_ascii=False).encode()).hexdigest())
    retrieval_ok = True
except Exception as exc:
    retrieval_ok = False
    st.error(f'检索器初始化失败：{exc}')
    st.stop()

if 'jd_text' not in st.session_state:
    st.session_state.jd_text = ''
if 'jd_result' not in st.session_state:
    st.session_state.jd_result = None
if 'last_plan_id' not in st.session_state:
    st.session_state.last_plan_id = None

st.title('RolePath')
st.markdown('**从职业探索到第一份实习：看清岗位要求、检查能力证据、制定可执行任务。**')
st.caption('粘贴任意岗位 JD 开始准备。未配置模型时，只能做不完整的关键词初筛；任务完成不代表能力已经验证。')

explore_tab, jd_tab, courses_tab, learning_tab, task_tab, notes_tab, debug_tab = st.tabs(['🧭 探索方向','📄 解析岗位 JD','📚 课程与题目','🗓️ 学习路径','✅ 学习任务','📝 学习笔记','🔎 资料问答'])

with explore_tab:
    st.subheader('还没有目标岗位？先探索实际工作内容')
    st.write('下面三个岗位是**教学演示方向**，不是实时招聘信息，也不代表所有公司的统一技能标准。')
    st.info('支持粘贴其他岗位 JD。规则解析有覆盖边界；LLM 可提取词库外要求，未找到课程的技能会明确标出。')
    con = connect()
    previous = recent_plan(con)
    con.close()
    if previous and st.button('恢复最近计划的 JD', key='restore_jd'):
        text = json.loads(previous['meta']).get('jd', '')
        if text:
            st.session_state.jd_text = text
            st.session_state.jd_result = json.loads(previous['meta']).get('parsed') or parse_jd(text)
            st.info('已恢复保存时的分析。若要使用最新解析规则，请在「解析岗位 JD」重新解析。')
    for role in ROLES:
        with st.container(border=True):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(f"**{role['name']}** · {role['kind']}")
                st.write(role['description'])
                st.caption('示例技能：' + ' · '.join(role['skills']))
            with col_b:
                if st.button('分析这个方向', key=f"select_{role['id']}", use_container_width=True):
                    st.session_state.jd_text = role['demo_jd']
                    st.session_state.jd_result = parse_jd(role['demo_jd'])
                    st.success('已载入演示岗位。切换到「解析岗位 JD」查看，并可替换为真实 JD。')

with jd_tab:
    st.subheader('把目标 JD 变成可检查的能力要求')
    st.write('直接粘贴 JD，或上传 TXT / MD / PDF、PNG / JPG / HEIC 图片。推荐使用真实岗位，解析结果会保留原文证据。')
    uploaded_jd = st.file_uploader('上传岗位 JD（可选）', type=UPLOAD_TYPES, key='jd_upload')
    st.text_area('岗位 JD 原文', key='jd_text', height=210, placeholder='粘贴岗位名称、职责、任职要求、优先条件和实习时间…')
    parse_mode = st.selectbox('解析方式', ['关键词初筛（不完整，无需 API）','LLM 结构化抽取（需 API Key）'], index=1 if is_configured() else 0)
    if st.button('解析岗位要求', type='primary', key='do_parse'):
        try:
            jd_text = read_upload(uploaded_jd) if uploaded_jd else st.session_state.jd_text
            if not jd_text.strip():
                st.session_state.jd_result = None
                st.warning('请粘贴 JD 或上传文件。')
            else:
                # Do not mutate widget state after text_area is instantiated.
                if parse_mode.startswith('LLM'):
                    if not is_configured():
                        raise ValueError('LLM 未配置：请填写 API Key 和模型名称，或选择不完整的关键词初筛。')
                    st.session_state.jd_result = parse_jd_with_llm(jd_text)
                else:
                    st.session_state.jd_result = parse_jd(jd_text)
        except Exception as exc:
            st.session_state.jd_result = None
            st.error(f'无法解析该 JD：{exc}')
    parsed = st.session_state.jd_result
    if parsed:
        st.caption('解析方式：' + parsed['mode'])
        if parsed['mode'].startswith('规则'):
            st.warning('下面只是词库命中，不是完整岗位分析，也不是重要性排名。完整拆解需要配置模型；请逐条核对下面的 JD 原文。')
        reqs = parsed['requirements']
        if reqs:
            st.dataframe([{'能力要求':x['skill'],'具体要求':x.get('detail', x['evidence']),'要求类别':x['priority'],'明确强调':x.get('importance','未标注'),'对应原文':x['evidence']} for x in reqs], hide_index=True, use_container_width=True)
        else:
            st.warning('未发现可识别的技能，请核查 JD 原文；规则词库并不覆盖所有岗位要求，可在下方补充。')
        with st.expander('逐条核对 JD：包含未识别内容', expanded=True):
            for row in parsed.get('source_review', []):
                st.write(f"{row['number']}. {row['text']}")
                st.caption('已关联：' + '、'.join(row['skills']) if row['skills'] else '尚未关联能力：请核对是否包含遗漏的职责、技能或条件。')
            st.caption('关联到一个标签不代表整条要求已经完整分析。')
        if parsed['constraints']:
            st.markdown('**可能的非技能条件（需人工确认）**')
            st.dataframe([{'类别':c['category'],'原文片段':c['text']} for c in parsed['constraints']],hide_index=True,use_container_width=True)
        st.info('学历、毕业年份、地点与实习时间请先自行确认；学习计划不能替代这些条件。')
        with st.expander('补充漏识别的岗位要求'):
            with st.form('add_requirement'):
                skill = st.text_input('技能或业务要求', max_chars=50)
                evidence = st.text_input('粘贴对应 JD 原文片段')
                priority = st.selectbox('要求类别', ['常规要求','加分项'])
                add = st.form_submit_button('补充要求')
            if add:
                if not skill.strip() or not evidence.strip() or evidence.strip() not in parsed['raw']:
                    st.error('请填写要求名称，并引用当前 JD 中真实存在的原文。')
                elif any(r['skill'] == skill.strip() for r in parsed['requirements']):
                    st.warning('该要求已存在。')
                else:
                    parsed['requirements'].append(dict(skill=skill.strip(), evidence=evidence.strip(), priority=priority, parser='人工补充'))
                    st.rerun()

with courses_tab:
    st.subheader('按 JD 选择课程与有来源的题目')
    prefer_bili = st.checkbox('相关性相同时优先 B 站', value=True, key='prefer_bili')
    st.caption('先匹配能力范围，再按具体要求的相关性排序，不按作者加权。当前是经过目录核查的资源库，不是实时全网搜索；没有匹配项时明确留空。课程质量依据目录与出处，未逐集评审。')
    parsed = st.session_state.jd_result
    if not parsed:
        st.info('先载入或解析一份 JD。')
    else:
        for group in coverage(parsed['requirements'], retriever, prefer_bili):
            r = group['requirement']
            with st.expander(r['skill']+' · '+r['priority']):
                st.write('JD 原文：'+r['evidence'])
                if not group['courses']:
                    st.warning('当前没有核验过的匹配课程，不自动安排无来源学习任务。')
                for hit in group['courses'][:3]:
                    c = hit.resource
                    st.markdown(f"**[{c['title']}]({c['url']})**")
                    st.write('对应学习内容：'+c.get('focus', {}).get(r['skill'], c['description']))
                    st.caption(f"发布方：{c.get('creator','官方资料/原发布方')} · 发布：{c.get('published','见原站')} · 本次学习预算约 {c.get('minutes_by_skill',{}).get(r['skill'],c['minutes'])} 分钟（含练习，非整课时长）")
                    for chapter in c.get('chapters',{}).get(r['skill'],[]):
                        st.markdown(f"[{chapter['title']}]({chapter['url']}) · {chapter['seconds']//60} 分钟")
                    st.caption(c.get('quality_basis','按资源目录技能标签匹配')+'；'+c.get('freshness_note','内容时效以原站为准'))
                    st.caption('核查：'+c.get('checked_at','原有资源，本轮未核查')+' · '+c.get('verification',''))
                if not group['questions']:
                    st.caption('暂无核查过的对应题目。计划可安排成果练习，但不会标成企业真题。')
                for q in group['questions']:
                    st.markdown(f"练习：[{q['title']}]({q['url']})")
                    st.caption(q['source_type']+' · '+q['source']+' · '+q['published'])
                    st.write(q['summary'])
        st.info('题目只提供简要说明与原站入口，未提供企业内部题库；面经是作者回忆，不代表任何公司的当前考试内容。')

with learning_tab:
    st.subheader('能力证据与个性化学习计划')
    parsed = st.session_state.jd_result
    if not parsed or not parsed['requirements']:
        st.info('先去「探索方向」载入一个演示 JD，或在「解析岗位 JD」中提交真实 JD。')
    else:
        col_a, col_b = st.columns([3, 2])
        with col_a:
            claimed = st.multiselect('你认为自己接触过哪些技能？（仅作自述，不视为已掌握）', list(dict.fromkeys(ALL_SKILLS+[r['skill'] for r in parsed['requirements']])))
            notes = st.text_area('项目经历、学习成果或作品说明（可选）', height=130, placeholder='例：我做过RAG知识库问答项目，记录了检索结果；尚未做系统评测。')
            upload_evidence = st.file_uploader('上传自己的项目文档或学习笔记（可选）', type=UPLOAD_TYPES, key='profile_upload')
            if upload_evidence:
                try:
                    notes = notes + '\n' + read_upload(upload_evidence)[:18000]
                    st.caption('材料已在本地读取；提及某技能不等于能力已通过验证。')
                except Exception as exc:
                    st.error(f'读取个人资料失败：{exc}')
        with col_b:
            hours = st.slider('每周可用学习时间（小时）', min_value=1, max_value=30, value=8)
            days = st.slider('准备周期（天）', min_value=3, max_value=90, value=14)
            st.caption('规划器会遵循总时间预算。固定练习任务只是候选计划，不代表标准化课时。')
        evaluated = assess(parsed['requirements'], claimed, notes)
        st.markdown('**当前能力证据（未经技能测验）**')
        st.dataframe([{'技能':a['skill'],'JD要求':a['priority'],'状态':a['status']} for a in evaluated], hide_index=True, use_container_width=True)
        if st.button('生成并保存学习路径', type='primary', key='make_plan'):
            tasks,summary=plan_tasks(evaluated,retriever,hours,days,prefer_bili=st.session_state.prefer_bili)
            if not tasks:
                st.error('没有可安排的任务：请检查课程缺口或增加时间预算。未覆盖原有计划。')
            else:
                conn=connect()
                try:
                    pid=save_plan(conn,parsed['raw'].splitlines()[0][:100],tasks,{'hours_per_week':hours,'days':days,'jd':parsed['raw'],'summary':summary,'retrieval':retriever_name,'parsed':parsed})
                    st.session_state.last_plan_id=pid
                finally:
                    conn.close()
                st.success(f'已保存 {len(tasks)} 个任务。到「学习任务」可标记完成。')
        conn=connect()
        try:
            latest=recent_plan(conn)
            plan_items=tasks_for(conn,latest['id']) if latest else []
        finally:
            conn.close()
        if latest:
            meta=__import__('json').loads(latest['meta'])
            summary=meta.get('summary',{})
            a,b,c=st.columns(3)
            a.metric('计划总预算',f"{summary.get('capacity_minutes',0)/60:.1f}小时")
            b.metric('已安排任务',len(plan_items))
            c.metric('待安排技能',len(summary.get('unscheduled_skills',[])))
            st.caption('这里展示最近一次保存的计划；修改 JD 或时间后，请重新生成计划。每个学习预算是本次章节学习与练习时间，不是学完整套课程。')
            if summary.get('missing_resources'):
                st.warning('课程缺口（未编造资源）：'+'、'.join(summary['missing_resources']))
            if summary.get('unscheduled_skills'):
                st.warning('当前计划未安排：' + '、'.join(summary['unscheduled_skills']))
            st.dataframe([{'预计日期':t['due'],'技能':t['skill'],'类型':t['kind'],'任务':t['title'],'分钟':t['minutes'],'学习链接':t['resource_url'] or '无'} for t in plan_items],hide_index=True,use_container_width=True)
            sessions = [{'日期':ss['date'],'任务':t['title'],'分钟':ss['minutes']} for t in plan_items for ss in t.get('sessions',[])]
            if sessions:
                with st.expander('每日学习安排（较长任务分天完成）'):
                    st.dataframe(sessions, hide_index=True)

with task_tab:
    st.subheader('执行任务 · 保存进度')
    conn=connect()
    try:
        latest=recent_plan(conn)
        if not latest:
            st.info('目前还没有学习计划。去「学习路径」创建。')
        else:
            tasks=tasks_for(conn,latest['id'])
            stats = study_stats(conn, latest['id'])
            a,b,c = st.columns(3)
            a.metric('连续学习', f"{stats['streak']} 天")
            b.metric('本周记录', f"{stats['week_minutes']} 分钟")
            c.metric('累计学习日', stats['days'])
            if stats['days'] >= 7:
                st.success('已积累 7 个学习日，坚持记录，也记得复习与休息。')
            elif stats['days'] >= 1:
                st.success('已迈出第一步！下一次记录可以写下遇到的一个问题。')
            if tasks:
                with st.form('daily_study'):
                    tid = st.selectbox('今天学习的任务', [t['id'] for t in tasks], format_func=lambda v: next(t['title'] for t in tasks if t['id']==v))
                    mins = st.number_input('今天学习分钟数', min_value=1, max_value=1440, value=30, step=5)
                    reflection = st.text_area('今天学到了什么、遇到了什么问题？', max_chars=3000)
                    logged = st.form_submit_button('保存今日打卡')
                if logged:
                    try:
                        log_study(conn, tid, int(mins), reflection)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                st.caption('同一任务同一天重复保存会更新记录，不重复累计。打卡与完成任务都是自报，不代表能力已验证。')
                if stats['logs']:
                    with st.expander('学习记录'):
                        st.dataframe([{'日期':r['day'],'任务':r['title'],'分钟':r['minutes'],'记录':r['reflection']} for r in stats['logs']], hide_index=True)
            completed=sum(t['status']=='已完成' for t in tasks)
            st.progress(completed / len(tasks) if tasks else 0, text=f'任务记录完成：{completed}/{len(tasks)}（不代表能力已验证）')
            for t in tasks:
                with st.container(border=True):
                    c1,c2=st.columns([5,1])
                    with c1:
                        st.markdown(f"**{t['title']}**")
                        st.caption(f"{t['due']} · {t['minutes']}分钟 · {t['kind']} · {t['priority']}")
                        st.write('提交/自查标准：' + t['acceptance'])
                        if t.get('matching_reason'):
                            st.caption(t['matching_reason'])
                        for chapter in t.get('chapters',[]):
                            st.markdown(f"观看分集：[{chapter['title']}]({chapter['url']})")
                        if t.get('question'):
                            q = t['question']
                            st.markdown(f"题目来源：[{q['title']}]({q['url']})")
                            st.caption(q['source_type']+' · '+q['source'])
                        if t['resource_url']:
                            st.markdown(f"学习资源：[打开 {t['resource_title']}]({t['resource_url']})")
                    with c2:
                        checked=st.checkbox('已完成',value=t['status']=='已完成',key=f"task_{t['id']}")
                        if checked != (t['status']=='已完成'):
                            set_task_status(conn,t['id'],'已完成' if checked else '待完成')
                            st.rerun()
            st.info('本版“完成”仅代表用户自报。自动评测练习作品和动态重排属于下一版本。')
    finally:
        conn.close()

with notes_tab:
    render_notes(st.session_state.jd_result)

with debug_tab:
    st.subheader('向你的学习资料提问')
    st.write('从你上传的笔记和资料中查找依据。例如：我记录过哪些面试问题？提示词评测需要注意什么？这里与「学习笔记」共用资料；学习笔记负责汇总，这里回答具体问题。')
    st.caption('无需 API Key 就能查找相关段落；生成带来源的回答需要配置 API Key。')
    st.caption('支持多张 PNG、JPG、HEIC/HEIF 照片，每张最多 5MB。图片在运行服务上识别文字，请在学习笔记中核对识别结果；暂不理解纯图表，手写文字可能有误。')
    knowledge_file = st.file_uploader('上传个人学习资料 / 官方文档（单份 ≤5MB，PDF ≤40页）', type=UPLOAD_TYPES, accept_multiple_files=True, key='knowledge_file')
    if st.button('保存资料', key='import_knowledge', disabled=not knowledge_file):
        con = connect()
        try:
            for file in knowledge_file:
                try:
                    with st.spinner('正在读取 ' + file.name + '…'):
                        pages = pages_from_upload(file)
                        _, count = save_document(con, file.name, pages)
                    st.success(file.name + ('：已保存。' if count else '：已存在，未重复保存。'))
                except Exception as exc:
                    st.error(file.name + '：未保存，' + str(exc))
        finally:
            con.close()
    con = connect()
    try:
        docs = get_documents(con)
        chunks = get_chunks(con)
        st.caption(f'当前有 {len(docs)} 份资料，与学习笔记共用。')
        for doc in docs:
            d1,d2=st.columns([5,1])
            d1.write(f"📄 {doc['filename']}")
            if d2.button('删除',key=f"del_{doc['id']}"):
                delete_document(con,doc['id'])
                st.rerun()
        doc_question = st.text_input('向上传的知识库提问', value='这份文档讲了什么？', key='document_question')
        if retriever_name=='dense':
            doc_hits = search_dense(con,doc_question,retriever,top_k=4)
        else:
            doc_hits = search_lexical(con,doc_question,top_k=4)
        if doc_question.strip() and chunks:
            for h in doc_hits:
                with st.expander(f"{h.filename} · 第{h.page}页 · 相关原文"):
                    st.write(h.text)

            if st.button('根据资料回答',key='answer_document', disabled=not is_configured()):
                try:
                    answer=answer_from_document(doc_question,doc_hits)
                    st.markdown(answer['answer'])
                    st.caption(answer['mode'])
                    if answer['usage']: st.json(answer['usage'])
                except Exception as exc:
                    st.error(f'真实 API 请求失败：{exc}')
        elif not chunks:
            st.info('还没有资料，请先上传笔记或文档。')
    finally:
        con.close()

st.divider()
st.caption('RolePath V0.1 · 仅供学习与产品测试 · 规则识别、课程索引与能力状态都需要人工校验。')
