"""Job-specific live research, auto-run from the current role, skills and stage."""
import logging
import streamlit as st
from .i18n import t as tr,label,language
from .cloud_settings import cloud_mode
from .credits import run_ai_task,task_notice
from .llm import is_configured
from .matching import learning_requirements
from .db import connect, recent_plan, tasks_for
from .resource_research import research_resources,scope_for,planning_materials

KINDS={'course':'课程','reference':'专业资料','practice':'平台练习','company_bank':'作者标注的企业题目（未经企业确认）','interview_recollection':'用户回忆面经（非官方真题）'}


def saved_research(scope):
    current=st.session_state.get('_resource_research')
    if current and current['scope']==scope:return current
    if cloud_mode() and st.session_state.get('_account_client'):
        client=st.session_state['_account_client']
        rows=client.table('rp_ai_runs').select('result').eq('user_id',st.session_state['_account_id']).eq('task','resources').eq('status','succeeded').order('created_at',desc=True).limit(10).execute().data
        for row in rows:
            if row['result'].get('scope')==scope:
                st.session_state['_resource_research']=row['result']
                return row['result']
    return None


def selected_materials(parsed):
    result=saved_research(scope_for(parsed))
    if not result:return [],[]
    selected=st.session_state.get('_research_selected',{}).get(result['created_at'],[])
    return planning_materials(result,selected)


def _learning_stage():
    conn = connect()
    try:
        plan = recent_plan(conn)
        if not plan:
            return '入门准备：尚未生成学习计划'
        tasks = tasks_for(conn, plan['id'])
        done = sum(t['status'] == '已完成' for t in tasks)
        if not done:
            return '计划已生成，尚未开始执行'
        return f'计划执行中：已完成 {done}/{len(tasks)} 个任务'
    finally:
        conn.close()


def render_research(parsed):
    scope=scope_for(parsed)
    result=saved_research(scope)
    if not parsed:
        st.info(tr('先载入或解析一份 JD，AI 才会按岗位自动查找资料。'))
        return
    role=(parsed.get('orientation') or {}).get('role_name') or parsed['raw'].splitlines()[0][:40]
    requirements=learning_requirements(parsed)
    st.caption(tr('进入资料区后 AI 会按当前岗位、技能与学习阶段自动查找；仅发送岗位方向和能力名称，不会发送你的学习笔记。'))
    err_key='_research_error_'+scope[:12]
    if result is None and not st.session_state.get(err_key):
        if not is_configured():
            logging.getLogger('rolepath.research').warning('auto research skipped: LLM not configured')
            st.info(tr('AI 暂时不可用，请稍后重试'))
        else:
            try:
                with st.status(tr('正在自动查找适合你的资料…'),expanded=True) as status:
                    def progress(stage,count):
                        status.write(tr('正在搜索公开来源…') if stage=='search' else tr('正在读取具体网页…') if stage=='read' else tr('正在筛选内容并核对出处…'))
                    result=run_ai_task('resources',lambda:research_resources(role,requirements,scope,language(),progress,_learning_stage()))
                    st.session_state['_resource_research']=result
                    status.update(label=tr('已找到可查看出处的学习资料'),state='complete',expanded=False)
            except Exception as exc:
                logging.getLogger('rolepath.research').warning('auto research failed: %s', exc)
                st.session_state[err_key]=True
    if result is None and st.session_state.get(err_key):
        st.error(tr('AI 暂时不可用，请稍后重试'))
        if st.button(tr('重试查找'),key='research_retry'):
            st.session_state.pop(err_key,None)
            st.rerun()
    if not result:return
    st.write(result['overview'])
    st.caption(tr('检索于 {0} · {1} 次搜索 · {2} 次网页读取',result['created_at'][:10],result['trace']['search_calls'],result['trace']['read_calls']))
    if result['trace']['stopped_at_tool_budget']:
        st.caption(tr('本轮已达到检索步数上限，结果只包含已读取的资料。'))
    choices=st.session_state.setdefault('_research_selected',{})
    chosen=choices.setdefault(result['created_at'],[])
    for i, item in enumerate(result['items']):
        with st.container(border=True, key=f'rp_resource_{i}'):
            st.caption(label(KINDS[item['kind']])+' · '+item['creator'])
            st.link_button(item['title'],item['url'],use_container_width=True)
            st.markdown(tr('**为什么推荐给我**'))
            st.write(item['reason'])
            if item.get('date_evidence'):
                st.caption(tr('原文中的时间信息（请结合上下文核对）：'))
                st.text(item['date_evidence'])
            else:
                st.caption(tr('来源未提供可核对的发布时间或更新时间。'))
            if item.get('source_claim'):
                st.caption(tr('原站声明（未经企业确认）：')+item['source_claim'])
            st.write(tr('先学什么：')+item['learn'])
            st.caption(tr('建议本次投入 {0} 分钟；这是学习预算，不是整课时长。',item['minutes']))
            with st.expander(tr('推荐依据与访问说明')):
                st.text(item['evidence'])
                if item['access_note']:st.caption(item['access_note'])
                st.caption(tr('访问权限和是否免费请以原站当前页面为准。'))
                st.caption(tr('依据千问网页工具返回内容筛选，未完整试听视频；面经和题库的企业归属以原站标注为准。'))
            if parsed:
                checked=st.checkbox(tr('用于我的学习计划'),value=item['source_id'] in chosen,key='research_pick_'+result['created_at']+'_'+item['source_id'])
                if checked and item['source_id'] not in chosen:chosen.append(item['source_id'])
                elif not checked and item['source_id'] in chosen:chosen.remove(item['source_id'])
    if result['gaps']:
        with st.expander(tr('还缺哪些资料')):
            for gap in result['gaps']:st.write(gap)
    if parsed and chosen:
        from .ui import go_to
        st.button(tr('用所选资料制定计划 →'),on_click=go_to,args=('学习计划',),key='research_to_plan')
