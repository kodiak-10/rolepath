import json
from pathlib import Path
import pytest
from rolepath import llm, db
from rolepath.matching import learning_requirements

BROAD_JD='AI产品实习生\n对AI产品有兴趣，具备产品思维，善于跨团队沟通协作。'


def orientation():
    return dict(role_name='AI产品实习生',overview='从用户问题出发，设计AI功能并验证效果，交付产品方案与评估记录。',
        concepts=[dict(name=n,explanation=e) for n,e in [('大模型','根据输入生成内容，也会出现事实错误。'),('提示词','向模型说明任务、约束与输出方式。'),('效果评估','用测试案例和标准比较输出。')]],
        learning=[dict(skill=s,reason=r,goal=g) for s,r,g in [('需求分析','产品工作先理解用户问题，属于入门建议。','写出一个用户场景与三条待验证假设。'),('LLM','先了解AI应用的能力与边界。','记录两个AI应用的适用场景与失败案例。'),('竞品分析','用相同任务比较产品方案。','比较两款AI应用并记录差异。')]],
        interview=[dict(question=q,assesses=a) for q,a in [('你会如何选择一个AI应用场景？','展示用户问题和验证方法。'),('模型生成错误内容如何处理？','说明错误边界与人工核验。'),('如何比较两款AI产品？','使用一致的用户任务和标准。')]])


def respond(monkeypatch,requirements=None,guide=None):
    payload={'requirements':requirements or [],'orientation':orientation() if guide is None else guide}
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:(json.dumps(payload,ensure_ascii=False),{'total_tokens':100}))


def test_broad_jd_has_advice_without_inventing_employer_requirements(monkeypatch):
    respond(monkeypatch)
    result=llm.parse_jd_with_llm(BROAD_JD,with_orientation=True)
    assert result['requirements']==[]
    assert result['orientation']['overview']
    assert result['source_review'][0]['text']=='AI产品实习生'
    advice=learning_requirements(result)
    assert {r['skill'] for r in advice}=={'需求分析','LLM','竞品分析'}
    assert all(r['origin']=='guidance' and r['priority']=='岗位入门建议' for r in advice)
    assert learning_requirements(result,False)==[]


def test_explicit_requirement_wins_over_duplicate_advice(monkeypatch):
    respond(monkeypatch,[dict(skill='需求分析',detail='调研需求',priority='常规要求',evidence_ids=['L1'])])
    result=llm.parse_jd_with_llm('负责需求分析',with_orientation=True)
    rows=learning_requirements(result)
    assert rows[0]['evidence']=='负责需求分析' and rows[0]['priority']=='常规要求'
    assert len([r for r in rows if r['skill']=='需求分析'])==1


@pytest.mark.parametrize('case',['missing','link','empty','duplicate'])
def test_invalid_advice_fails_instead_of_saving_partial_result(monkeypatch,case):
    guide=orientation()
    if case=='missing': guide={}
    elif case=='link': guide['overview']='学习 https://invented.example/course'
    elif case=='empty': guide['learning'][0]['reason']=''
    else: guide['learning'][1]['skill']=guide['learning'][0]['skill']
    respond(monkeypatch,guide=guide)
    with pytest.raises(ValueError,match='未保存该结果'):
        llm.parse_jd_with_llm(BROAD_JD,with_orientation=True)


def test_general_role_does_not_require_a_preset_profession(monkeypatch):
    guide=orientation();guide['role_name']='审计实习生'
    guide['learning']=[dict(skill=s,reason='审计岗位入门建议',goal='制作一页学习记录') for s in ['审计底稿','函证流程','会计凭证核查']]
    respond(monkeypatch,guide=guide)
    result=llm.parse_jd_with_llm('审计实习生，认真负责',with_orientation=True)
    assert not result['requirements']
    assert learning_requirements(result)[0]['skill']=='审计底稿'
    assert 'SQL' not in {r['skill'] for r in learning_requirements(result)}


def test_broad_role_ui_has_courses_interview_prompts_and_opt_in_plan(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('ROLEPATH_CLOUD','0')
    monkeypatch.setenv('LLM_API_KEY','test-not-real')
    monkeypatch.setenv('LLM_MODEL','test-model')
    monkeypatch.setattr(db,'DB_FILE',str(tmp_path/'guide.db'))
    respond(monkeypatch)
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30)
    at.session_state['_language']='zh';at.run()
    at.radio[0].set_value('岗位分析').run()
    at.text_area(key='jd_text').set_value(BROAD_JD).run()
    at.button(key='do_parse').click().run()
    assert not at.exception
    at.radio[0].set_value('课程与题目').run()
    assert any('从用户问题出发' in m.value for m in at.markdown)
    assert any('Coze' in m.value or '生成式人工智能' in m.value for m in at.markdown)
    assert any('面试准备' in e.label for e in at.expander)
    assert not any('JD 原文：产品工作先理解' in m.value for m in at.markdown)
    at.radio[0].set_value('学习计划').run()
    assert at.checkbox(key='include_guidance').value
    at.button(key='make_plan').click().run()
    assert not at.exception
    con=db.connect();plans=db.all_plans(con);tasks=db.tasks_for(con,plans[0]['id']);con.close()
    assert tasks and all(t['requirement_origin']=='guidance' for t in tasks)
    assert all('对应 JD 原文' not in t['matching_reason'] for t in tasks)
    at.checkbox(key='include_guidance').uncheck().run()
    assert not at.exception


def test_product_and_ai_tool_foundations_have_reviewed_domestic_material():
    from rolepath.catalog import load_resources
    from rolepath.retrieval import LexicalRetriever
    from rolepath.matching import course_matches,reviewed_domestic
    from rolepath.jd import parse_jd
    parsed=parse_jd('AI产品实习生，具备基本产品思维，能够进行AI工具使用。')
    assert {'产品思维','AI应用基础'}<={r['skill'] for r in parsed['requirements']}
    ret=LexicalRetriever(load_resources())
    for skill in ['产品思维','AI应用基础']:
        hits=course_matches(dict(skill=skill,evidence=skill),ret)
        assert hits and any(reviewed_domestic(h.resource) for h in hits)
        assert all('AI辅助编程' not in h.resource['skills'] for h in hits)


def test_role_advice_is_not_limited_to_catalogue_and_does_not_confuse_ai_tools_with_coding(monkeypatch):
    def message(content,system,**kwargs):
        context=json.loads(content)
        assert 'learning_catalog' not in context
        assert '普通AI工具使用应选择AI应用基础' in system
        assert '需要参考词表外的能力时直接列出' in system
        assert '产品思维、逻辑表达、沟通协作' in system
        return json.dumps(dict(requirements=[],orientation=orientation()),ensure_ascii=False),None
    monkeypatch.setattr(llm,'_message',message)
    assert llm.parse_jd_with_llm(BROAD_JD,with_orientation=True)['orientation']


@pytest.mark.parametrize('invalid',[None,[],{'ability':'用户研究'},'', 'x'*901])
def test_invalid_interview_assessment_is_not_filled_or_coerced(monkeypatch,invalid):
    guide=orientation()
    if invalid is None:
        guide['interview'][0].pop('assesses')
    else:
        guide['interview'][0]['assesses']=invalid
    respond(monkeypatch,guide=guide)
    with pytest.raises(ValueError,match='岗位建议字段无效：assesses'):
        llm.parse_jd_with_llm(BROAD_JD,with_orientation=True)


def test_jd_request_uses_strict_schema_with_required_interview_text(monkeypatch):
    from types import SimpleNamespace
    calls=[]
    payload=dict(requirements=[],orientation=orientation())
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(payload,ensure_ascii=False)))],usage=None)
    monkeypatch.setattr(llm,'client',lambda:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    result=llm.parse_jd_with_llm(BROAD_JD,with_orientation=True)
    assert result['orientation']['interview']==payload['orientation']['interview']
    assert len(calls)==1
    fmt=calls[0]['response_format']
    assert fmt['type']=='json_schema' and fmt['json_schema']['strict'] is True
    root=fmt['json_schema']['schema']
    assert root['required']==['requirements','orientation']
    row=root['properties']['orientation']['properties']['interview']['items']
    assert row['required']==['question','assesses'] and row['additionalProperties'] is False
    assert row['properties']['assesses']['type']=='string'
    assert row['properties']['assesses']['minLength']==1
    assert row['properties']['assesses']['maxLength']==900
    ids=root['properties']['requirements']['items']['properties']['evidence_ids']['items']['enum']
    assert ids==['L1','L2']


def test_same_skill_in_required_and_preferred_is_rejected_without_silent_merge(monkeypatch):
    rows=[dict(skill='数据分析',priority=priority,evidence_ids=[line],detail='分析数据',importance='未标注')
          for priority,line in [('常规要求','L1'),('加分项','L2')]]
    respond(monkeypatch,requirements=rows)
    with pytest.raises(ValueError,match='重复能力'):
        llm.parse_jd_with_llm('分析用户行为数据\n数据分析能力优先',with_orientation=True)
