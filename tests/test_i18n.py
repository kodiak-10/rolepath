import ast
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from rolepath import db
from rolepath.i18n import EN
ROOT=Path(__file__).resolve().parents[1]

def test_catalog_covers_static_ui_messages():
    for p in [ROOT/'app.py', *(ROOT/'rolepath').glob('*ui.py'), ROOT/'rolepath/cloud_auth.py', ROOT/'rolepath/cloud_settings.py', ROOT/'rolepath/browser_session.py']:
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='tr':
                assert node.args[0].value in EN

def test_switch_keeps_draft_plan_and_location(monkeypatch,tmp_path):
    monkeypatch.setenv('ROLEPATH_CLOUD','0')
    monkeypatch.setattr(db,'DB_FILE',str(tmp_path/'ui.sqlite3'))
    at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45).run()
    assert not at.exception
    assert at.selectbox(key='_language').value=='en'
    assert at.radio(key='page').options[0]=='Home'
    at.button(key='select_ai_product').click().run()
    at.text_area(key='jd_text').input('自定义岗位：SQL').run()
    at.selectbox(key='_language').set_value('zh').run()
    assert not at.exception
    assert at.session_state.page=='岗位分析'
    assert at.text_area(key='jd_text').value=='自定义岗位：SQL'
    assert at.radio(key='page').options[0]=='我的空间'
    at.selectbox(key='_language').set_value('en').run()
    assert at.text_area(key='jd_text').value=='自定义岗位：SQL'
    at.radio(key='page').set_value('学习计划').run()
    at.button(key='make_plan').click().run()
    plan=at.session_state['_selected_plan_id']
    for lang in ['zh','en']:
        at.selectbox(key='_language').set_value(lang).run()
        for page in ['我的空间','岗位分析','课程与题目','学习计划','学习任务','学习笔记','历史记录']:
            at.session_state['page']=page
            at.run()
            assert not at.exception, (lang,page)
        assert at.session_state['_selected_plan_id']==plan

def test_chinese_link_preference(monkeypatch,tmp_path):
    monkeypatch.setenv('ROLEPATH_CLOUD','0')
    monkeypatch.setattr(db,'DB_FILE',str(tmp_path/'ui.sqlite3'))
    at=AppTest.from_file(str(ROOT/'app.py'))
    at.query_params['lang']='zh'
    at.run()
    assert at.selectbox(key='_language').value=='zh'
