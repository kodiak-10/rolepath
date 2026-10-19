"""Per-browser Supabase authentication. No shared clients or administrator keys."""
import base64
import json
from urllib.parse import urlparse


def validate_public_config(url, key):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co') or parsed.username or parsed.port or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('请配置项目的 HTTPS Supabase URL。')
    if key.startswith('sb_publishable_'):
        return
    try:
        part = key.split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))
    except (ValueError, IndexError, TypeError) as exc:
        raise ValueError('请使用项目的 publishable 或 anon key。') from exc
    if not isinstance(claims, dict) or claims.get('role') != 'anon':
        raise ValueError('网页登录禁止使用 service_role 或 secret key。')


def new_client(url, key):
    validate_public_config(url, key)
    from supabase import create_client
    return create_client(url, key)


def require_login():
    """Call before any private data is loaded. Returns a verified session client."""
    import streamlit as st
    try:
        from pathlib import Path
        config = json.loads((Path(__file__).resolve().parents[1] / 'deploy' / 'public_config.json').read_text())
        url = config['SUPABASE_URL']
        key = config['SUPABASE_PUBLISHABLE_KEY']
        validate_public_config(url, key)
    except (KeyError, OSError, ValueError):
        st.error('账号服务尚未配置，不能进入个人空间。')
        st.stop()
    # Never use st.cache_resource: Supabase clients contain user tokens.
    if '_account_client' not in st.session_state:
        st.session_state['_account_client'] = new_client(url, key)
    client = st.session_state['_account_client']
    try:
        session = client.auth.get_session()
    except Exception:
        st.session_state.clear()
        st.error('登录已失效，请刷新页面后重新登录。')
        st.stop()
    if session:
        try:
            user = client.auth.get_user().user
            if not user:
                raise ValueError('No verified user')
        except Exception:
            st.session_state.clear()
            st.error('登录已失效，请重新登录。')
            st.stop()
        prior = st.session_state.get('_account_id')
        if prior and prior != user.id:
            st.session_state.clear()
            st.error('账户已变化，请重新登录。')
            st.stop()
        st.session_state['_account_id'] = user.id
        with st.sidebar:
            st.caption('已登录：' + (user.email or '个人账户'))
            if st.button('退出登录', key='account_logout'):
                try:
                    client.auth.sign_out()
                finally:
                    st.session_state.clear()
                st.rerun()
        return client, user.id
    st.title('登录 RolePath')
    st.write('登录后查看自己的笔记、学习计划与打卡记录。')
    action = st.radio('账户操作', ['登录', '注册'], horizontal=True)
    with st.form('account_login', clear_on_submit=True):
        email = st.text_input('邮箱', max_chars=254)
        password = st.text_input('密码', type='password', max_chars=128)
        submitted = st.form_submit_button(action)
    if submitted:
        if not email.strip() or not password:
            st.error('请填写邮箱和密码。')
        else:
            try:
                credentials = {'email': email.strip(), 'password': password}
                if action == '注册':
                    client.auth.sign_up(credentials)
                    if client.auth.get_session():
                        st.rerun()
                    st.success('注册申请已提交，请查收确认邮件后登录。')
                else:
                    client.auth.sign_in_with_password(credentials)
                    st.rerun()
            except Exception:
                st.error('暂未完成，请检查邮箱、密码及邮箱验证状态，或稍后重试。')
    st.stop()
