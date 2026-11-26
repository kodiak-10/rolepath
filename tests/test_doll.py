from pathlib import Path
from streamlit.testing.v1 import AppTest
from rolepath import db

APP = Path(__file__).resolve().parents[1] / 'app.py'


def launch(monkeypatch, tmp_path):
    monkeypatch.setenv('ROLEPATH_CLOUD', '0')
    monkeypatch.setenv('LLM_API_KEY', '')
    monkeypatch.setenv('LLM_MODEL', '')
    monkeypatch.setattr(db, 'DB_FILE', str(tmp_path / 'doll.sqlite3'))
    return AppTest.from_file(str(APP), default_timeout=45).run()


def open_workbench(at):
    at.button(key='select_funnel_analyst').click().run()
    at.radio[0].set_value('准备学习').run()
    at.button(key='make_plan').click().run()
    at.button(key='practice_open').click().run()
    assert at.session_state['page'] == '岗位实操'
    assert not at.exception


def test_doll_is_present_on_home_and_collapsed_by_default(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    assert at.button(key='doll_toggle')
    assert not at.chat_input


def test_doll_keeps_form_and_history_across_collapse_and_page_switch(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    open_workbench(at)
    # AppTest cannot read unsubmitted st.form values; real-browser preservation
    # of the half-filled form is covered by the Playwright acceptance pass.
    at.text_area(key='practice_cause').input('注册到激活流失最大，先查分母口径。').run()
    at.button(key='doll_toggle').click().run()
    assert not at.exception
    assert len(at.chat_input) == 1
    assert at.session_state['page'] == '岗位实操'
    assert at.button(key='practice_submit')
    at.session_state['workspace_note_chat'] = [
        {'role': 'user', 'content': '这张表怎么读？'},
        {'role': 'assistant', 'content': '先看环节人数，再算相邻环节的比值。'},
    ]
    at.run()
    assert len(at.chat_message) == 2
    at.button(key='doll_close').click().run()
    assert not at.chat_input
    assert at.button(key='practice_submit')
    at.radio[0].set_value('我的空间').run()
    at.radio[0].set_value('岗位实操').run()
    assert at.button(key='practice_submit')
    at.button(key='doll_toggle').click().run()
    assert len(at.chat_message) == 2
    assert at.session_state['page'] == '岗位实操'


def test_doll_unconfigured_states_limitation_and_disables_ai(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    at.button(key='doll_toggle').click().run()
    assert not at.exception
    assert any('AI is temporarily unavailable' in str(m.value) for m in at.info)
    quick = next(b for b in at.button if b.label == 'What does this role do?')
    assert quick.disabled


def test_doll_quick_questions_follow_the_page(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    at.button(key='doll_toggle').click().run()
    labels = {b.label for b in at.button}
    assert 'What does this role do?' in labels
    at.radio[0].set_value('准备学习').run()
    labels = {b.label for b in at.button}
    assert 'What should I do first today?' in labels
    assert 'How should I plan this week?' in labels

def test_doll_uploads_resume_and_follows_up(monkeypatch, tmp_path):
    import json
    from rolepath import llm

    at = launch(monkeypatch, tmp_path)
    monkeypatch.setenv('LLM_API_KEY', 'test')
    monkeypatch.setenv('LLM_MODEL', 'test')
    resume = 'Synthetic resume: helped a team review campaign data.'
    requests = []

    def message(content, *args, **kwargs):
        if content.startswith('页面上下文：'):
            requests.append(content)
            return 'Start by choosing a role you want to explore.', None
        requests.append(json.loads(content))
        return 'Explain what you did to review the campaign data.', None

    monkeypatch.setattr(llm, '_message', message)
    at.button(key='doll_toggle').click().run()
    at.chat_input[0].upload('resume.txt', resume.encode()).run()
    assert not at.exception
    assert requests[0]['resume'] == resume
    assert len(at.chat_message) == 2

    at.button(key='doll_close').click().run()
    at.button(key='doll_toggle').click().run()
    at.chat_input[0].set_value('What should I emphasize?').run()
    assert not at.exception
    assert requests[1]['resume'] == resume
    assert requests[1]['instruction'] == 'What should I emphasize?'
    assert requests[1]['conversation'][-1]['content'] == 'Explain what you did to review the campaign data.'

    at.button(key='dialog_note_reset').click().run()
    assert not at.chat_message
    assert 'workspace_resume_text' not in at.session_state
    at.button(key='doll_q_这个岗位做什么？').click().run()
    assert not at.exception
    assert 'What does this role do?' in requests[2]
    assert resume not in requests[2]
    assert at.session_state['workspace_note_chat'][-1]['content'] == 'Start by choosing a role you want to explore.'
