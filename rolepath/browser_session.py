"""Browser-local Supabase sessions; never stores model API keys or user records."""
import time
import streamlit as st
import streamlit.components.v2 as components

_STORAGE_JS = '''
export default function({data, setStateValue, parentElement}) {
  const marker = JSON.stringify(data);
  if (parentElement.__rpCommand === marker) return;
  parentElement.__rpCommand = marker;
  const key = 'rolepath.auth.v1';
  try {
    if (data.action === 'clear') localStorage.removeItem(key);
    if (data.action === 'write') localStorage.setItem(key, JSON.stringify(data.session));
    let session = JSON.parse(localStorage.getItem(key) || 'null');
    if (session && session.until <= Date.now()/1000) {
      localStorage.removeItem(key); session = null;
    }
    setStateValue('result', {id:data.id, session, available:true});
  } catch (_) {
    setStateValue('result', {id:data.id, session:null, available:false});
  }
}
'''
_bridge = components.component('rolepath_session', js=_STORAGE_JS)


def session_payload(session, until=None):
    return dict(access_token=session.access_token, refresh_token=session.refresh_token,
                until=until or int(time.time()) + 7*24*3600)


def browser_session(command):
    result = _bridge(key='browser_auth', data=command, on_result_change=lambda: None, height=0)
    return result.result


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
        # Local credentials must still be removed if the network is unavailable.
        import logging
        logging.getLogger(__name__).warning('Remote sign-out could not be confirmed')
    finally:
        st.session_state.clear()
        st.session_state['_auth_command'] = dict(action='clear', id=str(uuid.uuid4()))


def restore_browser_session(client):
    command = st.session_state.get('_auth_command', dict(action='read', id='initial'))
    result = browser_session(command)
    if not result or result.get('id') != command['id']:
        st.info('正在恢复登录…')
        st.stop()
    if not result['available']:
        st.warning('浏览器不允许保存登录状态；关闭页面后需重新验证邮箱。')
    if not st.session_state.get('_auth_browser_loaded'):
        saved = result.get('session')
        if isinstance(saved, dict) and saved.get('until', 0) > time.time():
            try:
                response = client.auth.set_session(saved['access_token'], saved['refresh_token'])
                if not response.session:
                    raise ValueError('No session')
                st.session_state['_auth_until'] = saved['until']
            except Exception:
                st.error('无法恢复上次登录。可以重试，或清除这台设备的登录后重新验证。')
                if st.button('重试恢复登录'):
                    st.rerun()
                if st.button('重新验证邮箱'):
                    logout()
                    st.rerun()
                st.stop()
        st.session_state['_auth_browser_loaded'] = True
    return result
