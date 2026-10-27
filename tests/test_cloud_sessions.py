import pytest
import streamlit as st
from rolepath.cloud_settings import model_setting
from rolepath.db import connect


def test_cloud_never_uses_owner_api_credentials(monkeypatch):
    monkeypatch.setenv('ROLEPATH_CLOUD', '1')
    monkeypatch.setenv('LLM_API_KEY', 'owner-private-key')
    state = {}
    monkeypatch.setattr(st, 'session_state', state)
    assert model_setting('LLM_API_KEY') == ''
    state['visitor_LLM_API_KEY'] = 'visitor-key'
    assert model_setting('LLM_API_KEY') == 'visitor-key'
    state.clear()
    assert model_setting('LLM_API_KEY') == ''


def test_cloud_requires_login_before_database_access(monkeypatch):
    monkeypatch.setenv('ROLEPATH_CLOUD', '1')
    monkeypatch.setattr(st, 'session_state', {})
    with pytest.raises(RuntimeError, match='请先登录'):
        connect()


def test_two_sessions_do_not_share_clients(monkeypatch):
    monkeypatch.setenv('ROLEPATH_CLOUD', '1')
    first, second = object(), object()
    monkeypatch.setattr(st, 'session_state', {'_account_id': 'a', '_account_client': first})
    a = connect()
    monkeypatch.setattr(st, 'session_state', {'_account_id': 'b', '_account_client': second})
    b = connect()
    assert a.client is first and b.client is second
    assert a.user_id == 'a' and b.user_id == 'b'


def test_blank_key_keeps_existing_configuration(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('ROLEPATH_CLOUD','1')
    at=AppTest.from_string('''import streamlit as st
from rolepath.cloud_settings import render_model_settings
st.session_state.setdefault('visitor_LLM_API_KEY', 'example-test-key')
st.session_state.setdefault('visitor_LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
st.session_state.setdefault('visitor_LLM_MODEL', 'qwen-plus')
render_model_settings()
''').run()
    next(b for b in at.button if b.label=='Apply settings').click().run()
    assert not at.exception and not at.error
    assert at.session_state['visitor_LLM_API_KEY']=='example-test-key'

@pytest.mark.parametrize('endpoint,allowed', [
    ('https://maas.qianwenaiapi.com/compatible-mode/v1',True),
    ('https://dashscope.aliyuncs.com/compatible-mode/v1',True),
    ('https://example.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',True),
    ('https://maas.qianwenaiapi.com.evil.example/compatible-mode/v1',False),
    ('https://maas.qianwenaiapi.com@evil.example/compatible-mode/v1',False),
    ('http://maas.qianwenaiapi.com/compatible-mode/v1',False),
])
def test_provider_endpoint_host_is_exact(endpoint,allowed):
    from rolepath.cloud_settings import valid_model_endpoint
    assert valid_model_endpoint(endpoint) is allowed
