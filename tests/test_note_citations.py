import json
import pytest
from rolepath import llm
from rolepath.notes import summarize_notes


def test_note_citation_preserves_ocr_text(monkeypatch):
    rows=[dict(id='doc:1:0',document_id='doc',filename='照片.HEIC',page=1,content='第一行\n  SQL：COUNT(*)\n识別错字保持原样。')]
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    def reply(content,system,**kwargs):
        assert 'S1' in content
        return json.dumps({'items':[{'kind':'总结','text':'记录了计数表达式。','source_ref':'S1'}]}),None
    monkeypatch.setattr(llm,'_message',reply)
    report=summarize_notes(rows)
    assert report['items'][0]['quote']==rows[0]['content']
    assert report['items'][0]['source_id']==rows[0]['id']


@pytest.mark.parametrize('ref',['S999',None,['S1']])
def test_unknown_or_invalid_note_reference_rejected(monkeypatch,ref):
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:(json.dumps({'items':[{'kind':'总结','text':'总结','source_ref':ref}]}),None))
    with pytest.raises(ValueError,match='原文编号'):
        summarize_notes([dict(id='a',document_id='d',filename='a',page=1,content='笔记原文')])


def test_instruction_and_history_reach_model_without_forced_full_summary(monkeypatch):
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    history=[{'role':'user','content':'先出题'},{'role':'assistant','content':'COUNT 的作用是什么？'}]
    def reply(content,system,**kw):
        data=json.loads(content)
        assert data['instruction']=='我的答案：COUNT 是计数。请反馈。'
        assert data['conversation']==history
        assert '未看到原始图片' in system
        return json.dumps({'items':[{'kind':'反馈','text':'模型解释：计数这个理解正确。','source_ref':'S1'}]}),None
    monkeypatch.setattr(llm,'_message',reply)
    rows=[dict(id=str(i),document_id=str(i),filename=str(i),page=1,content='COUNT 用于计数。') for i in range(2)]
    report=summarize_notes(rows,instruction='我的答案：COUNT 是计数。请反馈。',history=history)
    assert report['instruction'].startswith('我的答案')
    assert report['history']==history
    assert len(report['items'])==1


def test_instruction_length_rejected_before_api(monkeypatch):
    monkeypatch.setattr(llm,'is_configured',lambda:True)
    with pytest.raises(ValueError,match='3000'):
        summarize_notes([{'id':'a'}],instruction='字'*3001)
