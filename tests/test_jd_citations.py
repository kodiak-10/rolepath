import json
import pytest
from rolepath import llm


def test_multiline_evidence_is_read_from_original_not_copied_by_model(monkeypatch):
    text='用 Vibe Coding 产出交互\nHTML /Web 原型。\n加分项\n熟悉工业级 Agent\n生产链路。'
    payload={'requirements':[
        {'skill':'HTML','priority':'常规要求','detail':'制作网页原型','evidence_ids':['L1','L2']},
        {'skill':'Agent','priority':'加分项','detail':'理解生产链路','evidence_ids':['L4','L5']} ]}
    def respond(content,system,**kwargs):
        assert json.loads(content)['sources']['L2']=='HTML /Web 原型。'
        return json.dumps(payload),None
    monkeypatch.setattr(llm,'_message',respond)
    result=llm.parse_jd_with_llm(text)
    assert result['requirements'][0]['evidence']=='用 Vibe Coding 产出交互\nHTML /Web 原型。'
    assert result['requirements'][1]['evidences']==['熟悉工业级 Agent','生产链路。']
    assert result['source_review'][-1]['skills']==['Agent']


@pytest.mark.parametrize('ids',[['L99'],['L1','L1'],[],['L1',1]])
def test_invalid_source_references_fail_explicitly(monkeypatch,ids):
    payload={'requirements':[{'skill':'HTML','priority':'常规要求','evidence_ids':ids}]}
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:(json.dumps(payload),None))
    with pytest.raises(ValueError,match='未保存该结果'):
        llm.parse_jd_with_llm('HTML 原型')
