from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from rolepath import db, practice
from rolepath.catalog import load_roles
from rolepath.jd import parse_jd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.py'


def funnel_role():
    return next(r for r in load_roles() if r['id'] == 'funnel_analyst')


def good_submission(**over):
    sub = dict(step=practice.TARGET_STEP, rate_b=30.0, rate_a=75.0,
               cause='渠道 B 的短信验证码到达率低，用户收不到验证码而放弃。',
               verification='分渠道对比短信发送成功率日志，并做小流量 A/B 实验验证。')
    sub.update(over)
    return sub


def test_demo_jd_opens_practice_without_login():
    assert practice.applies_to(parse_jd(funnel_role()['demo_jd']))
    assert not practice.applies_to(parse_jd(load_roles()[0]['demo_jd']))
    assert not practice.applies_to(None)


def test_reference_rates_come_from_data():
    assert practice.TARGET_RATE_B == pytest.approx(30.0)
    assert practice.TARGET_RATE_A == pytest.approx(75.0)
    rows = practice.data_rows()
    assert rows[-1]['渠道'] == '合计'
    assert rows[-1]['落地页访问'] == 14000


def test_grade_full_marks_and_weak_submission():
    fb = practice.grade(good_submission())
    assert fb['score'] == 100
    assert fb['next_steps'][-1] == 'extend_window'
    weak = practice.grade(dict(step=0, rate_b=15.0, rate_a=45.0, cause='体验不好', verification='看一下'))
    assert weak['score'] < 40
    assert {'recompute', 'check_denominator', 'hypothesis', 'design_test'} <= set(weak['next_steps'])


def test_wrong_denominator_is_flagged():
    fb = practice.grade(good_submission(rate_b=900 / 6000 * 100, rate_a=2700 / 8000 * 100))
    assert fb['step_ok'] and not fb['rate_b_ok'] and not fb['rate_a_ok']
    assert 'check_denominator' in fb['next_steps']


def test_attempt_roundtrip_survives_reconnect(tmp_path):
    path = tmp_path / 'p.db'
    con = db.connect(path)
    sub = good_submission()
    fb = practice.grade(sub)
    db.save_practice_attempt(con, practice.PRACTICE_ID, sub, fb)
    con.close()
    con = db.connect(path)
    latest = db.latest_practice_attempt(con, practice.PRACTICE_ID)
    con.close()
    assert latest['submission'] == sub
    assert latest['feedback'] == fb


def launch(monkeypatch, tmp_path):
    monkeypatch.setenv('ROLEPATH_CLOUD', '0')
    monkeypatch.setattr(db, 'DB_FILE', str(tmp_path / 'ui.sqlite3'))
    return AppTest.from_file(str(APP), default_timeout=45).run()


def test_workbench_flow_and_record_survives_refresh(monkeypatch, tmp_path):
    at = launch(monkeypatch, tmp_path)
    assert not at.exception
    at.button(key='select_funnel_analyst').click().run()
    assert at.session_state.page == '岗位分析'
    at.radio[0].set_value('学习计划').run()
    at.button(key='make_plan').click().run()
    assert not at.exception
    at.button(key='practice_open').click().run()
    assert at.session_state.page == '实习工作台'
    assert not at.exception
    step_box = at.selectbox(key='practice_step')
    step_box.set_value(step_box.options[practice.TARGET_STEP])
    at.number_input(key='practice_rate_b').set_value(30.0)
    at.number_input(key='practice_rate_a').set_value(75.0)
    at.text_area(key='practice_cause').input(good_submission()['cause'])
    at.text_area(key='practice_verification').input(good_submission()['verification'])
    at.button(key='practice_submit').click().run()
    assert not at.exception
    assert any(m.value == '100 / 100' for m in at.metric)
    at.button(key='practice_back').click().run()
    assert at.session_state.page == '学习计划'
    assert any(b.key == 'practice_resume' for b in at.button)
    # A fresh AppTest against the same database stands in for a browser refresh.
    fresh = AppTest.from_file(str(APP), default_timeout=45).run()
    fresh.radio[0].set_value('学习计划').run()
    assert not fresh.exception
    assert any(b.key == 'practice_resume' for b in fresh.button)
    assert any('Internship workbench' == option for option in fresh.radio[0].options)