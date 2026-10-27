"""Browser-local Supabase sessions; never stores model API keys or user records."""
from .i18n import t as tr, label, table, formatter
import time
import streamlit as st
import streamlit.components.v2 as components
_STORAGE_JS = "\nexport default function({data, setStateValue, parentElement}) {\n  const marker = JSON.stringify(data);\n  if (parentElement.__rpCommand === marker) return;\n  parentElement.__rpCommand = marker;\n  const key = 'rolepath.auth.v1';\n  try {\n    if (data.action === 'clear') localStorage.removeItem(key);\n    if (data.action === 'write') localStorage.setItem(key, JSON.stringify(data.session));\n    let session = JSON.parse(localStorage.getItem(key) || 'null');\n    if (session && session.until <= Date.now()/1000) {\n      localStorage.removeItem(key); session = null;\n    }\n    setStateValue('result', {id:data.id, session, available:true});\n  } catch (_) {\n    setStateValue('result', {id:data.id, session:null, available:false});\n  }\n}\n"
_bridge = components.component('rolepath_session', js=_STORAGE_JS)

def session_payload(session, until=None):
    return dict(access_token=session.access_token, refresh_token=session.refresh_token, until=until or int(time.time()) + 7 * 24 * 3600)

def browser_session(command, key='browser_auth'):
    result = _bridge(key=key, data=command, on_result_change=lambda: None, height=0)
    return result.result


def refresh_action_session():
    """Dialogs rerun independently of require_login; refresh before private access."""
    client = st.session_state.get('_account_client')
    expected = st.session_state.get('_account_id')
    try:
        session = client.auth.get_session() if client else None
        user = client.auth.get_user().user if session else None
        if not user or not expected or user.id != expected:
            raise ValueError('Account verification failed')
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning('Dialog authentication failed: type=%s', type(exc).__name__)
        st.error(tr('登录已失效，请关闭窗口并刷新页面重新登录。'))
        st.stop()
    saved = st.session_state.get('_auth_command', {}).get('session', {})
    if saved.get('access_token') != session.access_token or saved.get('refresh_token') != session.refresh_token:
        queue_session(session)


def sync_action_session():
    """Flush after actions, so a browser sync cannot interrupt a model request."""
    command = st.session_state.get('_auth_command')
    if command and command.get('action') == 'write':
        browser_session(command, key='note_dialog_auth')

def queue_session(session):
    import uuid
    payload = session_payload(session, st.session_state.get('_auth_until'))
    st.session_state['_auth_until'] = payload['until']
    st.session_state['_auth_command'] = dict(action='write', id=str(uuid.uuid4()), session=payload)

def logout():
    import uuid
    client = st.session_state.get('_account_client')
    try:
        if client:
            client.auth.sign_out()
    except Exception:
        import logging
        logging.getLogger(__name__).warning('Remote sign-out could not be confirmed')
    finally:
        st.session_state.clear()
        st.session_state['_auth_command'] = dict(action='clear', id=str(uuid.uuid4()))

def restore_browser_session(client):
    command = st.session_state.get('_auth_command', dict(action='read', id='initial'))
    result = browser_session(command)
    if not result or result.get('id') != command['id']:
        # Once restored, the verified server session can render while a storage
        # write is acknowledged. Stopping here would unmount and erase widgets.
        if st.session_state.get('_auth_browser_loaded'):
            return None
        st.info(tr('正在恢复登录…'))
        st.stop()
    if not result['available']:
        st.warning(tr('浏览器不允许保存登录状态；关闭页面后需重新验证邮箱。'))
    if not st.session_state.get('_auth_browser_loaded'):
        saved = result.get('session')
        if isinstance(saved, dict) and saved.get('until', 0) > time.time():
            try:
                response = client.auth.set_session(saved['access_token'], saved['refresh_token'])
                if not response.session:
                    raise ValueError('No session')
                st.session_state['_auth_until'] = saved['until']
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning('Session restore failed: type=%s status=%s code=%s', type(exc).__name__, getattr(exc, 'status', None), getattr(exc, 'code', None))
                st.error(tr('无法恢复上次登录。可以重试，或清除这台设备的登录后重新验证。'))
                if st.button(tr('重试恢复登录')):
                    st.rerun()
                if st.button(tr('重新验证邮箱')):
                    logout()
                    st.rerun()
                st.stop()
        st.session_state['_auth_browser_loaded'] = True
    return result
