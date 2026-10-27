from datetime import date, timedelta
from pathlib import Path
import json
import pytest
from rolepath.catalog import load_resources
from rolepath.jd import parse_jd
from rolepath.evidence import assess
from rolepath.retrieval import LexicalRetriever
from rolepath.planner import plan_tasks
from rolepath.matching import coverage, question_matches
from rolepath.db import connect, save_plan, log_study, study_stats
from rolepath.knowledge import save_document, delete_document
from rolepath.notes import note_inventory, summarize_notes, save_report, reports
from rolepath import llm

ROOT=Path(__file__).resolve().parents[1]


def test_transsion_requirements_and_constraints():
    result=parse_jd((ROOT/'data/transsion_jd.txt').read_text())
    req={r['skill']:r for r in result['requirements']}
    assert {'AIGC','多模态','海外业务','海外社媒','本地化','内容营销','视频生产','原型设计','PRD','项目协作'} <= req.keys()
    assert req['视频生产']['priority']=='加分项'
    assert req['内容营销']['priority']=='常规要求'
    assert '算法与数据结构' not in req and 'SQL' not in req
    constraints=' '.join(c['text'] for c in result['constraints'])
    assert '2027 届' in constraints and '每周可实习4天及以上' in constraints and '6个月优先' in constraints
    assert '深圳' in constraints


def test_bonus_section_and_arbitrary_llm_skill(monkeypatch):
    assert parse_jd('加分项：\n了解 SQL')['requirements'][0]['priority']=='加分项'
    monkeypatch.setattr(llm, '_message', lambda *a,**kw: (json.dumps({'requirements':[{'skill':'Kubernetes','priority':'常规要求','evidence_ids':['L1']}]}),None))
    assert llm.parse_jd_with_llm('熟悉 Kubernetes')['requirements'][0]['skill']=='Kubernetes'


def test_jd_course_choice_and_no_invented_coverage():
    ret=LexicalRetriever(load_resources())
    requirements=assess(parse_jd((ROOT/'data/transsion_jd.txt').read_text())['requirements'],[], '')
    groups=coverage(requirements, ret)
    assert all('PRD' in h.resource['skills'] for h in next(g for g in groups if g['requirement']['skill']=='PRD')['courses'])
    assert not next(g for g in groups if g['requirement']['skill']=='本地化')['courses']
    tasks, summary=plan_tasks(requirements,ret,8,14,start=date(2026,10,18))
    assert tasks and all(t['resource_url'] for t in tasks)
    assert not any(t['kind']=='算法题' for t in tasks)
    assert '本地化' in summary['missing_resources']
    assert sum(t['minutes'] for t in tasks)<=960
    daily={}
    for task in tasks:
        assert sum(s['minutes'] for s in task['sessions']) == task['minutes']
        for session in task['sessions']:
            daily[session['date']]=daily.get(session['date'],0)+session['minutes']
    assert max(daily.values())<=69
    assert all('2026-10-18'<=day<='2026-10-31' for day in daily)
    assert question_matches('算法与数据结构')[0]['source_type'].startswith('平台练习题')


def test_log_updates_without_duplicate_streak(tmp_path):
    con=connect(tmp_path/'test.db')
    pid=save_plan(con,'test',[{'id':'task','title':'学习'}],{})
    yesterday=date.today()-timedelta(days=1)
    log_study(con,'task',20,'复习',yesterday)
    log_study(con,'task',30,'练习')
    log_study(con,'task',40,'补充学习')
    stats=study_stats(con,pid)
    assert stats['days']==2 and stats['streak']==2 and stats['minutes']==60
    with pytest.raises(ValueError):log_study(con,'task',5,'')
    with pytest.raises(ValueError):log_study(con,'task',5,'提前',date.today()+timedelta(days=1))
    con.close()


def test_note_reports_require_real_quotes_and_all_documents(tmp_path,monkeypatch):
    con=connect(tmp_path/'notes.db')
    doc1,_=save_document(con,'one.md',[(1,'PRD 应该明确目标、边界以及验收方法。')])
    doc2,_=save_document(con,'two.md',[(1,'需求分析需要区分用户提出的方案和实际问题。')])
    rows,_=note_inventory(con,[doc1,doc2],[])
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    items=[dict(kind='总结',text='这是待核查的总结',source_ref=f'S{i}') for i,r in enumerate(rows,1)]
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:(json.dumps({'items':items}),None))
    report=summarize_notes(rows)
    rid=save_report(con,report)
    assert reports(con)[0][0]==rid
    items.pop()
    with pytest.raises(ValueError,match='覆盖'):summarize_notes(rows)
    items[0]['source_ref']='S999'
    with pytest.raises(ValueError):summarize_notes(rows)
    delete_document(con,doc1)
    assert not reports(con)
    con.close()


def test_note_summary_does_not_silently_truncate(monkeypatch):
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    with pytest.raises(ValueError,match='上限'):
        summarize_notes([dict(id='x',filename='a',page=1,content='文'*25000,document_id='a')])


def test_transsion_ui_and_daily_log(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('LLM_API_KEY','')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    app.radio[0].set_value('岗位分析').run()
    app.text_area(key='jd_text').set_value((ROOT/'data/transsion_jd.txt').read_text()).run()
    next(x for x in app.selectbox if x.label=='Analysis method').select('关键词初筛（不完整，无需 API）').run()
    app.button(key='do_parse').click().run()
    assert not app.exception
    assert '多模态' in [r['skill'] for r in app.session_state.jd_result['requirements']]
    app.radio[0].set_value('学习计划').run()
    app.button(key='make_plan').click().run()
    app.radio[0].set_value('学习任务').run()
    assert not app.exception
    next(x for x in app.text_area if x.label.startswith('What did you learn')).set_value('验收记录：核对了岗位原文与课程章节。')
    next(x for x in app.button if x.label=="Save today's check-in").click().run()
    assert not app.exception
    fresh=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert any(m.label=='Study streak' and m.value=='1 days' for m in fresh.metric)
    next(b for b in fresh.button if b.label=='Continue learning →').click().run()
    assert fresh.session_state.jd_result['raw'].startswith('职位：AI 产品实习生')


def test_notes_ui_persists_checked_report(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.chdir(tmp_path)
    con=connect()
    doc,_=save_document(con,'我的学习笔记.md',[(1,'PRD 应写明目标、范围及验收标准，便于团队评审。')])
    rows,_=note_inventory(con,[doc],[])
    con.close()
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    monkeypatch.setenv('LLM_API_KEY','test-not-real')
    monkeypatch.setenv('LLM_MODEL','test-model')
    payload={'items':[dict(kind='总结',text='笔记关注需求文档的评审要素。',source_ref='S1')]}
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:(json.dumps(payload),None))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    app.radio[0].set_value('岗位分析').run()
    app.text_area(key='jd_text').set_value((ROOT/'data/transsion_jd.txt').read_text()).run()
    next(x for x in app.selectbox if x.label=='Analysis method').select('关键词初筛（不完整，无需 API）').run()
    app.button(key='do_parse').click().run()
    app.radio[0].set_value('学习笔记').run()
    app.button(key='open_note_chat').click().run()
    app.chat_input[0].set_value('总结笔记').run()
    assert not app.exception
    fresh=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not fresh.exception
    fresh.radio[0].set_value('学习笔记').run()
    fresh.button(key='open_note_reports').click().run()
    assert any('笔记关注需求文档' in m.value for m in fresh.markdown)


def test_plan_does_not_skip_learning_to_fit_practice():
    ret=LexicalRetriever([r for r in load_resources() if r['id']=='bili003'])
    req=assess([{'skill':'内容营销','priority':'常规要求','evidence':'内容营销'}],[], '')
    tasks,summary=plan_tasks(req,ret,1,7)
    assert not tasks  # Selected lesson takes 72 min; cannot fit in 60 min.
    assert summary['unscheduled_skills']==['内容营销']
