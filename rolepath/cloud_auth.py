"""Per-browser Supabase authentication. No shared clients or administrator keys."""
import base64
import json
import logging
import re
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


def validate_email(email):
    email = email.strip()
    if len(email) > 254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        raise ValueError('请填写完整的邮箱地址。')
    return email


def send_email_code(client, email):
    email = validate_email(email)
    client.auth.sign_in_with_otp({
        'email': email, 'options': {'should_create_user': True},
    })
    return email


def verify_email_code(client, email, code):
    code = code.strip()
    if not code or not code.isascii() or not code.isdigit():
        raise ValueError('请输入邮件中的数字验证码。')
    result = client.auth.verify_otp({'email': email, 'token': code, 'type': 'email'})
    if not result.session or not result.user:
        raise ValueError('验证未完成，请重新获取验证码。')
    return result


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
    from .browser_session import restore_browser_session, queue_session
    browser_result = restore_browser_session(client)
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
        saved = browser_result.get('session') or {}
        if browser_result.get('available') and (saved.get('access_token') != session.access_token or saved.get('refresh_token') != session.refresh_token):
            queue_session(session)
            st.rerun()
        st.session_state['_account_id'] = user.id
        st.session_state['_account_email'] = user.email or '个人账户'
        return client, user.id
    st.title('登录 RolePath')
    st.write('用邮箱验证码登录，无需设置密码。首次验证成功后创建账号。')
    st.caption('同一邮箱对应同一份笔记、学习计划和打卡记录。在个人设备上保留登录 7 天；换浏览器或清除浏览器数据后需要重新验证。')
    pending_email = st.session_state.get('_otp_email')
    if not pending_email:
        with st.form('account_send_code'):
            email = st.text_input('邮箱', max_chars=254)
            send = st.form_submit_button('发送验证码')
            already = st.form_submit_button('已收到验证码，直接验证')
        if send or already:
            try:
                email = validate_email(email)
            except ValueError as exc:
                st.error(str(exc))
            else:
                # Verification is independent of delivery acknowledgement.
                st.session_state['_otp_email'] = email
                if send:
                    request_email_code(client, email, st.session_state)
                else:
                    st.session_state['_otp_notice'] = ('info', '请输入该邮箱收到的最新验证码。')
                st.rerun()
    else:
        st.write('验证邮箱：' + pending_email)
        level, message = st.session_state.get('_otp_notice', ('info', '请输入邮件中的最新验证码。'))
        getattr(st, level)(message)
        with st.form('account_verify_code', clear_on_submit=True):
            code = st.text_input('邮箱验证码', max_chars=10, type='password')
            submitted = st.form_submit_button('验证并登录')
        if submitted:
            try:
                result = verify_email_code(client, pending_email, code)
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error('验证失败：验证码可能不正确或已过期，请重新获取后再试。')
            else:
                queue_session(result.session)
                st.session_state.pop('_otp_email', None)
                st.session_state.pop('_otp_notice', None)
                st.rerun()
        if st.button('重新发送验证码'):
            request_email_code(client, pending_email, st.session_state)
            st.rerun()
        if st.button('更换邮箱'):
            st.session_state.pop('_otp_email', None)
            st.session_state.pop('_otp_notice', None)
            st.rerun()
    st.stop()


def request_email_code(client, email, state):
    """Keep delivery errors explicit without blocking server-side OTP verification."""
    try:
        send_email_code(client, email)
    except Exception as exc:
        import httpx
        from supabase_auth.errors import AuthApiError, AuthRetryableError
        # Never log exception messages: they may contain email addresses or request data.
        known = isinstance(exc, (AuthApiError, AuthRetryableError))
        code = getattr(exc, 'code', None) if known else None
        status = getattr(exc, 'status', None) if known else None
        logging.getLogger(__name__).warning('OTP send error: type=%s status=%s code=%s', type(exc).__name__, status, code)
        if status == 429 or code in ('over_email_send_rate_limit', 'over_request_rate_limit'):
            message = '发送过于频繁，请稍后再试。若已收到验证码，可直接在下方验证。'
        elif isinstance(exc, (httpx.TimeoutException, AuthRetryableError)):
            message = '发送请求未得到及时确认，无法确认邮件是否送达。若已收到验证码，可直接在下方验证。'
        else:
            message = '邮件服务返回错误，未确认发送成功。若已收到验证码，可直接在下方验证；未收到请稍后重试。'
        state['_otp_notice'] = ('warning', message)
    else:
        state['_otp_notice'] = ('success', '发送请求成功，请查看收件箱和垃圾邮件，输入最新验证码。')
