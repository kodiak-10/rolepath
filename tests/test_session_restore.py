from types import SimpleNamespace
from unittest.mock import Mock
import time
import pytest
from rolepath import browser_session as bs


def test_tokens_rotate_without_extending_remember_period(monkeypatch):
    state={'_auth_until':time.time()+3600}
    monkeypatch.setattr(bs.st,'session_state',state)
    bs.queue_session(SimpleNamespace(access_token='new-access',refresh_token='new-refresh'))
    assert state['_auth_command']['session']['until']==state['_auth_until']
    assert state['_auth_command']['session']['refresh_token']=='new-refresh'


def test_restore_calls_supabase_not_local_identity(monkeypatch):
    saved={'access_token':'access','refresh_token':'refresh','until':time.time()+3600}
    monkeypatch.setattr(bs.st,'session_state',{})
    monkeypatch.setattr(bs,'browser_session',lambda c:dict(id=c['id'],available=True,session=saved))
    client=Mock()
    client.auth.set_session.return_value=SimpleNamespace(session=object())
    bs.restore_browser_session(client)
    client.auth.set_session.assert_called_once_with('access','refresh')
    assert '_account_id' not in bs.st.session_state


def test_expired_browser_session_is_not_restored(monkeypatch):
    monkeypatch.setattr(bs.st,'session_state',{})
    monkeypatch.setattr(bs,'browser_session',lambda c:dict(id=c['id'],available=True,session={'until':0}))
    client=Mock()
    bs.restore_browser_session(client)
    client.auth.set_session.assert_not_called()


def test_logout_clears_user_data_and_schedules_browser_removal(monkeypatch):
    client=Mock()
    state={'_account_client':client,'visitor_LLM_API_KEY':'private','jd_result':{'private':'data'}}
    monkeypatch.setattr(bs.st,'session_state',state)
    bs.logout()
    client.auth.sign_out.assert_called_once()
    assert list(state)==['_auth_command']
    assert state['_auth_command']['action']=='clear'


def test_dialog_refreshes_expired_session_and_queues_browser_update(monkeypatch):
    from types import SimpleNamespace
    from streamlit.testing.v1 import AppTest
    from rolepath import browser_session as bridge
    rotated=SimpleNamespace(access_token='new-access',refresh_token='new-refresh')
    calls=[]
    auth=SimpleNamespace(get_session=lambda:(calls.append('refresh') or rotated),get_user=lambda:(calls.append('verify') or SimpleNamespace(user=SimpleNamespace(id='owner'))))
    monkeypatch.setattr(bridge,'queue_session',lambda session:calls.append(('persist',session)))
    at=AppTest.from_string('''import streamlit as st
from rolepath.browser_session import refresh_action_session
refresh_action_session()
st.write('private-read-authorized')
''')
    at.session_state['_account_client']=SimpleNamespace(auth=auth)
    at.session_state['_account_id']='owner'
    at.session_state['_auth_command']={'session':{'access_token':'old-access','refresh_token':'old-refresh'}}
    at.run()
    assert not at.exception
    assert calls==['refresh','verify',('persist',rotated)]
    assert any('private-read-authorized' in x.value for x in at.markdown)


def test_dialog_rejects_mismatched_identity_before_private_reads(monkeypatch):
    from types import SimpleNamespace
    from streamlit.testing.v1 import AppTest
    at=AppTest.from_string('''import streamlit as st
from rolepath.browser_session import refresh_action_session
refresh_action_session()
st.write('private-data-must-not-render')
''')
    at.session_state['_language']='zh'
    at.session_state['_account_client']=SimpleNamespace(auth=SimpleNamespace(get_session=lambda:object(),get_user=lambda:SimpleNamespace(user=SimpleNamespace(id='someone-else'))))
    at.session_state['_account_id']='owner';at.run()
    assert not at.exception and at.error
    assert not any('private-data-must-not-render' in x.value for x in at.markdown)


def test_dialog_browser_sync_uses_a_distinct_component_key(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from rolepath import browser_session as bridge
    calls=[]
    monkeypatch.setattr(bridge,'browser_session',lambda command,key:calls.append((command,key)))
    at=AppTest.from_string('''from rolepath.browser_session import sync_action_session
sync_action_session()
''')
    command={'action':'write','id':'rotation','session':{'access_token':'test'}}
    at.session_state['_auth_command']=command;at.run()
    assert not at.exception and calls==[(command,'note_dialog_auth')]


def test_browser_write_ack_does_not_unmount_verified_workspace(monkeypatch):
    from streamlit.testing.v1 import AppTest
    session=SimpleNamespace(access_token='access',refresh_token='refresh')
    user=SimpleNamespace(id='owner',email='owner@example.invalid')
    client=SimpleNamespace(auth=SimpleNamespace(get_session=lambda:session,get_user=lambda:SimpleNamespace(user=user)))
    monkeypatch.setattr(bs,'browser_session',lambda command:None)
    at=AppTest.from_string('''import streamlit as st
from rolepath.cloud_auth import require_login
require_login()
st.radio('nav',['Home','Resources'],key='page')
st.text_input('Role',key='role_query')
if st.session_state.pop('_auth_flush_requested',False):st.rerun()
''')
    at.session_state['_account_client']=client
    at.session_state['_account_id']='owner'
    at.session_state['_auth_browser_loaded']=True
    at.session_state['_auth_command']={'action':'write','id':'pending','session':{'access_token':'access','refresh_token':'refresh'}}
    at.run();at.radio[0].set_value('Resources').run();at.text_input[0].input('Hotel reception').run()
    assert not at.exception and not at.error
    assert at.radio[0].value=='Resources' and at.text_input[0].value=='Hotel reception'


def test_pending_browser_ack_still_requires_verified_server_identity(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(bs,'browser_session',lambda command:None)
    client=SimpleNamespace(auth=SimpleNamespace(get_session=lambda:object(),get_user=lambda:SimpleNamespace(user=SimpleNamespace(id='other'))))
    at=AppTest.from_string('''import streamlit as st
from rolepath.cloud_auth import require_login
require_login()
st.write('private-workspace')
''')
    at.session_state['_account_client']=client;at.session_state['_account_id']='owner'
    at.session_state['_auth_browser_loaded']=True;at.run()
    assert at.error and not any(x.value=='private-workspace' for x in at.markdown)


def test_rotation_rerun_keeps_existing_widget_state(monkeypatch):
    from streamlit.testing.v1 import AppTest
    calls=[]
    session=SimpleNamespace(access_token='rotated',refresh_token='rotated-refresh')
    user=SimpleNamespace(id='owner',email='owner@example.invalid')
    def browser(command):
        calls.append(command['action'])
        if command['action']=='read':return dict(id=command['id'],available=True,session={'access_token':'old','refresh_token':'old-refresh'})
        if calls.count('write')==1:return None
        return dict(id=command['id'],available=True,session=command['session'])
    monkeypatch.setattr(bs,'browser_session',browser)
    at=AppTest.from_string('''import streamlit as st
from rolepath.cloud_auth import require_login
require_login()
st.radio('nav',['Home','Resources'],key='page')
st.text_input('Role',key='role_query')
if st.session_state.pop('_auth_flush_requested',False):st.rerun()
''')
    at.session_state['_account_client']=SimpleNamespace(auth=SimpleNamespace(get_session=lambda:session,get_user=lambda:SimpleNamespace(user=user)))
    at.session_state['_account_id']='owner';at.session_state['_auth_browser_loaded']=True
    at.session_state['page']='Resources';at.session_state['role_query']='Mechanical design'
    at.run()
    assert not at.exception and at.radio[0].value=='Resources'
    assert at.text_input[0].value=='Mechanical design'
    assert calls[:2]==['read','write']
