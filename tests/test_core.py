import sqlite3
from datetime import date

import pytest

from rolepath.catalog import load_resources, load_roles
from rolepath.jd import parse_jd
from rolepath.evidence import assess
from rolepath.retrieval import LexicalRetriever
from rolepath.planner import plan_tasks
from rolepath.db import connect, recent_plan, save_plan, tasks_for, set_task_status


def test_catalog_has_real_http_urls_and_supported_skills():
    resources=load_resources()
    assert len(resources)>=10
    assert len(load_roles())>=2
    assert len({r['id'] for r in resources})==len(resources)
    assert all(r['url'].startswith('https://') and r['skills'] for r in resources)


def test_jd_separates_bonus_and_regular():
    parsed=parse_jd('岗位要求：熟悉 SQL，能够使用 Python 处理数据；有 Agent 项目经验者优先。每周至少4天。')
    mapped={x['skill']:x for x in parsed['requirements']}
    assert mapped['SQL']['priority']=='常规要求'
    assert mapped['Python']['priority']=='常规要求'
    assert mapped['Agent']['priority']=='加分项'
    assert any(x['category']=='到岗时间' for x in parsed['constraints'])


def test_sql_not_matched_inside_unrelated_english_word():
    assert not parse_jd('I know nosql skills').get('requirements')


def test_claimed_skill_never_marked_verified():
    rows=assess([{'skill':'SQL','priority':'常规要求','evidence':'熟悉SQL'}, {'skill':'PRD','priority':'常规要求','evidence':'PRD'}],['SQL'],'个人参加 SQL 项目')
    assert rows[0]['status']=='材料提及（待验证）'
    assert rows[1]['status']=='暂无证据'
    assert all('已验证' not in x['status'] for x in rows)


def test_retriever_targets_skill():
    ret=LexicalRetriever(load_resources())
    items=ret.search('SQL 分组聚合',skill='SQL',limit=3)
    assert items
    assert all('SQL' in x.resource['skills'] for x in items)
    assert items[0].method.startswith('TF-IDF')


def test_planner_budget_and_unknown_skill():
    ret=LexicalRetriever(load_resources())
    req=assess([{'skill':'SQL','priority':'常规要求','evidence':'熟悉SQL'}, {'skill':'Python','priority':'加分项','evidence':'Python加分'}],[], '')
    tasks,summary=plan_tasks(req,ret,hours_per_week=3,days=7,start=date(2026,10,17))
    assert sum(x['minutes'] for x in tasks)<=3*60
    assert tasks
    assert tasks[0]['skill']=='SQL'
    assert all('2026-10-' in t['due'] for t in tasks)


def test_persistence_sqlite(tmp_path):
    conn=connect(tmp_path/'test.db')
    try:
        pid=save_plan(conn,'测试岗位',[{'id':'abc','title':'学习SQL','minutes':60}],{'days':7})
        assert recent_plan(conn)['id']==pid
        assert tasks_for(conn,pid)[0]['status']=='待完成'
        set_task_status(conn,'abc','已完成')
        assert tasks_for(conn,pid)[0]['status']=='已完成'
        with pytest.raises(ValueError):
            set_task_status(conn,'abc','已验证')
    finally:
        conn.close()


def test_empty_jd_rejected():
    with pytest.raises(ValueError):
        parse_jd('   ')


def test_document_chunking_and_reference(tmp_path):
    from rolepath.knowledge import chunk_page, save_document, get_chunks, search_lexical, delete_document
    text='课程说明：RAG 通过在生成答案前检索外部资料来补充上下文。' * 30
    bits=chunk_page(text, size=200, overlap=30)
    assert len(bits)>1
    assert bits[0][-30:] == bits[1][:30]
    conn=connect(tmp_path/'doc.db')
    try:
        docid,n=save_document(conn,'rag_notes.txt',[(1,text)])
        assert n>=2
        docid2,n2=save_document(conn,'rag_notes.txt',[(1,text)])
        assert docid2==docid and n2==0
        hits=search_lexical(conn,'RAG 检索外部资料',top_k=3)
        assert hits and hits[0].filename=='rag_notes.txt'
        assert hits[0].page==1 and hits[0].id.startswith(docid)
        delete_document(conn,docid)
        assert not get_chunks(conn)
    finally:
        conn.close()


def test_chunking_rejects_invalid_parameters():
    from rolepath.knowledge import chunk_page
    with pytest.raises(ValueError):
        chunk_page('test',size=20)


def test_negative_self_description_not_evidence():
    rows=assess([{'skill':'SQL','priority':'常规要求','evidence':'SQL'}],[],'我不会 SQL，还没有学过。')
    assert rows[0]['status']=='暂无证据'


def test_no_project_is_not_project_evidence():
    row=assess([{'skill':'SQL','priority':'常规要求','evidence':'SQL'}],[], '我没有 SQL 项目')[0]
    assert row['status']=='暂无证据'
