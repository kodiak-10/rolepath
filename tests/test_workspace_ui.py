from pathlib import Path
from streamlit.testing.v1 import AppTest
from rolepath import db

APP = Path(__file__).resolve().parents[1] / 'app.py'


def launch(monkeypatch, tmp_path):
    monkeypatch.setenv('ROLEPATH_CLOUD', '0')
    monkeypatch.setattr(db, 'DB_FILE', str(tmp_path/'ui.sqlite3'))
    return AppTest.from_file(str(APP), default_timeout=45).run()


def test_home_navigation_and_draft_survive_page_changes(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    assert not at.exception
    assert not at.sidebar.children
    at.button(key='select_ai_product').click().run()
    assert not at.exception
    assert at.session_state['page'] == '岗位分析'
    assert 'AI 产品' in at.text_area(key='jd_text').value
    at.text_area(key='jd_text').input('产品岗位：要求需求分析和竞品分析。').run()
    at.radio(key='page').set_value('学习笔记').run()
    assert not at.exception
    at.radio(key='page').set_value('岗位分析').run()
    assert at.text_area(key='jd_text').value == '产品岗位：要求需求分析和竞品分析。'


def test_plan_without_visiting_courses_and_resume(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    at.button(key='select_ai_product').click().run()
    at.radio(key='page').set_value('学习计划').run()
    assert not at.exception
    at.button(key='make_plan').click().run()
    assert not at.exception
    at.radio(key='page').set_value('我的空间').run()
    assert not at.exception
    next(b for b in at.button if b.label=='Continue learning →').click().run()
    assert at.session_state['page'] == '学习任务'
    assert not at.exception
    assert len(at.checkbox)>0


def test_all_destinations_render(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    for page in ['岗位分析','课程与题目','学习计划','学习任务','学习笔记','我的空间']:
        at.radio(key='page').set_value(page).run()
        assert not at.exception, page


def test_history_reopens_the_selected_plan(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    at.button(key='select_ai_product').click().run()
    at.radio(key='page').set_value('学习计划').run()
    at.button(key='make_plan').click().run()
    first=at.session_state['_selected_plan_id']
    at.button(key='make_plan').click().run()
    assert at.session_state['_selected_plan_id'] != first
    at.radio(key='page').set_value('历史记录').run()
    assert not at.exception
    at.button(key='history_'+first).click().run()
    assert at.session_state['_selected_plan_id']==first
    assert at.session_state['page']=='学习任务'
    assert not at.exception


def test_chat_is_a_separate_window_and_does_not_change_location(monkeypatch,tmp_path):
    at=launch(monkeypatch,tmp_path)
    at.radio(key='page').set_value('学习笔记').run()
    assert not at.chat_input
    assert not at.text_area
    at.button(key='global_note_chat').click().run()
    assert not at.exception
    assert len(at.chat_input)==1
    assert at.session_state['page']=='学习笔记'
    at.session_state['_note_chat_open']=False
    at.run()
    assert not at.chat_input
    assert at.session_state['page']=='学习笔记'
