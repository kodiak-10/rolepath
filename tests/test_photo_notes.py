from pathlib import Path
from types import SimpleNamespace
import pytest
from rolepath import photo_notes, llm

PHOTO=(Path(__file__).parent/'fixtures/ocr-note.png').read_bytes()
ANSWER='## 照片内容总结\nGROUP BY 用于分组统计，COUNT 用于计数。\n\n## 测试题\n1. 分组统计每类订单时，要用什么语句？\n2. COUNT(*) 与 COUNT(字段) 有什么区别？\n3. 请写出按类别统计订单数的SQL。\n请先作答，我再逐题反馈。'


def response():
    return dict(answer=ANSWER,instruction='总结内容，然后出几道测试题',sources=[dict(ref='P1',filename='note.png')],created_at='test-time',source_type='photo_answer')


def test_original_photo_and_instruction_sent_in_one_call(monkeypatch):
    import json
    calls=[]
    def message(content,system,**kwargs):
        calls.append(content)
        assert '不输出供程序解析的内部JSON' in system
        assert '等待用户作答后再逐题反馈' in system
        return ANSWER, {'total_tokens':50}
    monkeypatch.setattr(llm,'_message',message)
    result=photo_notes.analyze_photos([('note.png',PHOTO)],'总结内容，然后出几道测试题','zh')
    assert len(calls)==1
    assert calls[0][2]['image_url']['url'].startswith('data:image/jpeg;base64,')
    assert json.loads(calls[0][0]['text'])['instruction']=='总结内容，然后出几道测试题'
    assert result['answer']==ANSWER
    assert result['sources']==[dict(ref='P1',filename='note.png')]
    assert result['source_type']=='photo_answer'
    assert 'pages' not in result and 'items' not in result


@pytest.mark.parametrize('raw',['',None,{'answer':'wrong transport type'}])
def test_empty_or_non_text_provider_result_is_not_accepted(monkeypatch,raw):
    monkeypatch.setattr(llm,'_message',lambda *a,**k:(raw,None))
    with pytest.raises(ValueError,match='未返回内容'):
        photo_notes.analyze_photos([('note.png',PHOTO)],'总结')


def test_uncertainty_and_answer_are_not_rewritten(monkeypatch):
    answer='P1 第2行字段名[无法辨认]。无法确认它是 price 还是 prize，请补拍。'
    monkeypatch.setattr(llm,'_message',lambda *a,**k:(answer,None))
    assert photo_notes.analyze_photos([('note.png',PHOTO)],'解释')['answer']==answer


def test_multi_photo_sources_are_server_assigned_and_follow_up_keeps_context(monkeypatch):
    import json
    history=[dict(role='user',content='出三道题'),dict(role='assistant',content=ANSWER)]
    def message(content,system,**kwargs):
        assert json.loads(content[0]['text'])['conversation']==history
        assert [part['text'] for part in content if part['type']=='text'][1:]==['Image P1','Image P2']
        return '反馈：你对 GROUP BY 的作用理解正确，下一步检查 COUNT 的空值规则。',None
    monkeypatch.setattr(llm,'_message',message)
    result=photo_notes.analyze_photos([('one.png',PHOTO),('two.png',PHOTO)],'第一题用 GROUP BY，请给我反馈',history=history)
    assert result['sources']==[dict(ref='P1',filename='one.png'),dict(ref='P2',filename='two.png')]


def test_provider_failure_is_explicit_and_not_automatically_retried(monkeypatch):
    calls=[]
    def fail(*a,**kw):
        calls.append(1)
        raise TimeoutError('request timed out')
    monkeypatch.setattr(llm,'_message',fail)
    with pytest.raises(TimeoutError):photo_notes.analyze_photos([('note.png',PHOTO)],'总结')
    assert len(calls)==1


def test_limits_and_cloud_legacy_ocr_stop_before_model(monkeypatch):
    with pytest.raises(ValueError):photo_notes.prepare_photo(b'invalid','fake.exe')
    monkeypatch.setenv('ROLEPATH_CLOUD','1')
    from rolepath.image_text import read_image
    with pytest.raises(ValueError,match='旧版自动识别已停用'):read_image(PHOTO,'note.png')
    monkeypatch.setattr(llm,'_message',lambda *a,**k:pytest.fail('must not call model'))
    with pytest.raises(ValueError):photo_notes.analyze_photos([('a.png',PHOTO)]*5,'test')


def test_reviewed_ai_record_saved_without_model_call(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from rolepath.db import connect
    from rolepath.knowledge import get_chunks
    monkeypatch.setenv('ROLEPATH_CLOUD','0')
    monkeypatch.setattr(photo_notes,'analyze_photos',lambda *a,**k:pytest.fail('saving must not call model'))
    dbfile=str(tmp_path/'review.db')
    at=AppTest.from_string(f'''import streamlit as st
from rolepath.photo_notes_ui import render_photo_review
from rolepath.db import connect
con=connect({dbfile!r})
render_photo_review(con, st.session_state['photo_note_result'])
con.close()
''',default_timeout=30)
    at.session_state['_language']='zh';at.session_state['photo_note_result']=response();at.run()
    assert not at.exception
    assert at.button(key='photo_answer_save').disabled
    at.text_area[0].input(ANSWER+'\n用户核对记录：第三题还没有作答。').run()
    at.checkbox[0].check().run();at.button(key='photo_answer_save').click().run()
    assert not at.exception
    con=connect(dbfile);saved=get_chunks(con)[0]['content'];con.close()
    assert 'AI 生成、用户核对' in saved and '用户核对记录' in saved and 'note.png' in saved


def test_failed_photo_input_is_kept_for_manual_retry(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from rolepath import db,note_chat_ui
    monkeypatch.setenv('ROLEPATH_CLOUD','0');monkeypatch.setenv('LLM_API_KEY','test');monkeypatch.setenv('LLM_MODEL','test')
    monkeypatch.setattr(db,'DB_FILE',str(tmp_path/'chat.db'))
    calls=[]
    def analyze(photos,instruction,*a,**kw):
        calls.append(instruction)
        if len(calls) in (1,3): raise TimeoutError('test-timeout')
        return response()
    monkeypatch.setattr(note_chat_ui,'analyze_photos',analyze)
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30)
    at.session_state['_language']='zh';at.session_state['workspace_note_photos']=[('note.png',PHOTO)];at.run()
    at.button(key='global_note_chat').click().run()
    at.chat_input[0].set_value('总结内容，然后出几道测试题').run()
    assert not at.exception
    assert calls==['总结内容，然后出几道测试题']
    assert at.session_state['workspace_photo_pending']==calls[0]
    assert at.session_state['workspace_note_photos'][0][1]==PHOTO
    assert at.button(key='retry_photo_request')
    at.button(key='retry_photo_request').click().run()
    assert not at.exception and len(calls)==2
    assert at.session_state['workspace_note_chat'][-1]['content']==ANSWER
    assert 'workspace_photo_error' not in at.session_state
    at.chat_input[0].set_value('请解释第二题').run()
    assert not at.exception and len(calls)==3
    assert at.session_state['workspace_photo_result']['answer']==ANSWER
    assert at.session_state['workspace_photo_pending']=='请解释第二题'


def test_photo_ui_translations_complete():
    import ast
    from rolepath.i18n import EN
    source=Path(photo_notes.__file__).with_name('photo_notes_ui.py').read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='t':
            assert node.args[0].value in EN
