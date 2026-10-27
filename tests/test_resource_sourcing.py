from types import SimpleNamespace
from urllib.parse import urlparse
from rolepath.catalog import load_resources, load_questions
from rolepath.matching import course_matches
from rolepath.retrieval import LexicalRetriever


def test_reviewed_domestic_preference_preserves_skill_scope_and_can_be_disabled():
    local=dict(id='local',skills=['SQL'],domestic_platform=True,checked_at='2026-10-26',quality_basis='SELECT and GROUP BY chapters')
    remote=dict(id='remote',skills=['SQL'])
    wrong=dict(id='wrong',skills=['Python'],domestic_platform=True,checked_at='2026-10-26',quality_basis='Python chapters')
    hits=[SimpleNamespace(resource=local,score=.5),SimpleNamespace(resource=remote,score=.9),SimpleNamespace(resource=wrong,score=1)]
    ret=SimpleNamespace(search=lambda *a,**kw:list(hits))
    req={'skill':'SQL','evidence':'SQL GROUP BY'}
    assert [h.resource['id'] for h in course_matches(req,ret)]==['local','remote']
    assert [h.resource['id'] for h in course_matches(req,ret,False)]==['remote','local']


def test_domestic_catalog_has_real_chapters_and_not_one_creator():
    resources=load_resources()
    assert len({r['id'] for r in resources})==len(resources)
    added=[r for r in resources if r['id'].startswith('cn')]
    assert len(added)>=9
    assert len({r['creator'] for r in added if r.get('platform')=='B站'})>=3
    for r in added:
        assert r['checked_at'] and r['quality_basis'] and r['access_note']
        assert urlparse(r['url']).scheme=='https'
        for skill, chapters in r.get('chapters',{}).items():
            assert skill in r['skills']
            assert all(c['seconds']>0 and '?p=' in c['url'] for c in chapters)
    hits=course_matches({'skill':'SQL','evidence':'SQL GROUP BY 聚合函数'},LexicalRetriever(resources))
    assert hits[0].resource['id']=='cn001'


def test_corporate_claims_distinguish_platform_and_recalled_sources():
    questions=load_questions()
    assert len({q['id'] for q in questions})==len(questions)
    assert len(questions)==12
    allowed={'platform_problem','company_bank','company_archive','interview_recall'}
    for q in questions:
        assert q['provenance'] in allowed and q['access_note']
        assert urlparse(q['url']).scheme=='https'
        if q['provenance']=='company_archive':
            assert '历史' in q['source_type'] and '未获企业' in q['source_type']
        if q['provenance']=='interview_recall':
            assert '非官方真题' in q['source_type']
    assert all('小红书' not in q['source'] for q in questions)


def test_course_page_uses_domestic_preference_without_ai_call(monkeypatch,tmp_path):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from rolepath import db
    from rolepath.jd import parse_jd
    monkeypatch.setenv('ROLEPATH_CLOUD','0')
    monkeypatch.setenv('LLM_API_KEY','')
    monkeypatch.setattr(db,'DB_FILE',str(tmp_path/'ui.db'))
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30)
    at.session_state['_language']='zh'
    at.session_state['page']='课程与题目'
    at.session_state['jd_result']=parse_jd('数据分析实习岗位，要求 SQL 聚合与分组查询。')
    at.run()
    assert not at.exception
    assert not any(c.key=='prefer_domestic' for c in at.checkbox)
    assert not any('先匹配岗位能力，再优先' in c.value for c in at.caption)
    assert any('MySQL数据库入门到大牛' in m.value for m in at.markdown)
    assert any('SQL1 查找最晚入职员工' in m.value for m in at.markdown)
    assert not any('MySQL 8.4 官方参考手册' in m.value for m in at.markdown)
    at.session_state['_prefer_domestic']=False
    at.run()
    assert not at.exception
    assert not any('MySQL 8.4 官方参考手册' in m.value for m in at.markdown)
