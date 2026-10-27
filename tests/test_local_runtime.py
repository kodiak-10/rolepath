import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest
from rolepath import llm
from rolepath.db import connect
from rolepath.knowledge import search_dense

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('payload', [
    {'requirements': [None]},
    {'requirements': [{'skill': 'SQL', 'priority': '常规要求', 'evidence_ids': ['L999']}]},
    {'requirements': [{'skill': 'SQL', 'priority': '错误', 'evidence_ids': ['L1']}]},
    {'requirements': []},
])
def test_invalid_llm_output_raises(monkeypatch, payload):
    monkeypatch.setattr(llm, '_message', lambda *a, **kw: (json.dumps(payload), None))
    with pytest.raises(ValueError, match='未通过'):
        llm.parse_jd_with_llm('要求熟悉 SQL')


def test_valid_llm_output(monkeypatch):
    payload = {'requirements': [{'skill': 'SQL', 'priority': '常规要求', 'evidence_ids': ['L1']}]}
    monkeypatch.setattr(llm, '_message', lambda *a, **kw: (json.dumps(payload), None))
    result = llm.parse_jd_with_llm('要求熟悉 SQL')
    assert result['mode'].startswith('LLM')
    assert result['requirements'][0]['skill'] == 'SQL'


def test_deleting_last_document_clears_vector_index(tmp_path):
    deleted = []
    collection = SimpleNamespace(get=lambda **kw: {'ids': ['old-chunk']}, delete=lambda ids: deleted.extend(ids))
    dense = SimpleNamespace(client=SimpleNamespace(get_or_create_collection=lambda *a, **kw: collection))
    con = connect(tmp_path / 'test.db')
    try:
        assert search_dense(con, 'question', dense) == []
        assert deleted == ['old-chunk']
    finally:
        con.close()


def test_ui_plan_persists_and_missing_key_is_explicit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('LLM_API_KEY', '')
    monkeypatch.setenv('LLM_MODEL', '')
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    assert not app.exception
    app.button(key='select_ai_product').click().run()
    assert not app.exception
    app.text_area(key='jd_text').set_value('要求熟悉 SQL 和需求分析；有 RAG 项目经验者优先；每周至少4天。').run()
    app.button(key='do_parse').click().run()
    assert len(app.session_state.jd_result['requirements']) == 3
    app.radio(key='page').set_value('学习计划').run()
    for slider in app.slider:
        if slider.label == 'Weekly study time (hours)':
            slider.set_value(2)
        elif slider.label == 'Preparation period (days)':
            slider.set_value(7)
    app.button(key='make_plan').click().run()
    assert not app.exception
    con = connect()
    rows = con.execute('SELECT payload FROM tasks').fetchall()
    assert rows and sum(json.loads(row['payload'])['minutes'] for row in rows) <= 120
    app.radio(key='page').set_value('学习任务').run()
    next(c for c in app.checkbox if c.key and c.key.startswith('task_')).check().run()
    assert con.execute("SELECT COUNT(*) FROM tasks WHERE status='已完成'").fetchone()[0] == 1
    con.close()
    fresh = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    fresh.radio(key='page').set_value('学习任务').run()
    assert next(c for c in fresh.checkbox if c.key and c.key.startswith('task_')).value
    app.radio(key='page').set_value('岗位分析').run()
    next(x for x in app.selectbox if x.label=='Analysis method').select('LLM 结构化抽取（需 API Key）').run()
    app.button(key='do_parse').click().run()
    assert app.session_state.jd_result is None
    assert any('LLM 未配置' in error.value for error in app.error)
    assert not app.exception


def test_upload_validation_and_no_key(monkeypatch):
    from io import BytesIO
    from rolepath.ingest import read_upload
    from rolepath.knowledge import pages_from_upload
    file = BytesIO('SQL 学习笔记：分组聚合和关联查询。'.encode('utf-8-sig'))
    file.name = 'notes.md'
    assert read_upload(file).startswith('SQL')
    assert pages_from_upload(file)[0][0] == 1
    file.name = 'notes.exe'
    with pytest.raises(ValueError):
        read_upload(file)
    monkeypatch.setenv('LLM_API_KEY', '')
    monkeypatch.setenv('LLM_MODEL', '')
    assert llm.grounded_answer('SQL', [])['mode'] == '未生成'
    assert llm.answer_from_document('SQL', [])['mode'] == '未生成'
