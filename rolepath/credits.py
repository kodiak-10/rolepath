"""Server-side AI task accounting. User JWTs cannot mutate the credit ledger."""
from contextvars import ContextVar
import json
import uuid
from pathlib import Path
from .cloud_settings import managed_ai, server_setting

_usage = ContextVar('ai_usage', default=None)

def record_usage(usage):
    records = _usage.get()
    if records is not None:
        records.append(usage)


def execute_task(store, user_id, task, operation, daily_limit, request_id=None):
    """Reserve before generation, charge only a validated result, preserve usage on failure.

    A network error while settling is deliberately not treated as a failed model task:
    the database may already have committed. Never refund a possibly successful run.
    """
    request_id = request_id or str(uuid.uuid4())
    run = store.rpc('rp_ai_reserve', dict(p_user=user_id, p_id=request_id,
                    p_task=task, p_daily_limit=daily_limit)).execute().data
    if run['status'] == 'succeeded':
        return run['result']
    if run['status'] == 'pending' and not run.get('execute'):
        raise ValueError('This request is already running; it will not be executed twice.')
    if run['status'] != 'pending':
        raise ValueError('This request has already failed. Start a new task.')
    records = []
    token = _usage.set(records)
    try:
        try:
            result = operation()
            # Ensure the result is serializable before asking the ledger to settle.
            json.dumps(result, allow_nan=False)
            if result is None:
                raise ValueError('The AI task did not produce a result.')
        except Exception:
            store.rpc('rp_ai_finish', dict(p_user=user_id, p_id=request_id,
                      p_success=False, p_usage=records, p_result=None)).execute()
            raise
        # A successful result remains recoverable in the user's usage history.
        settled = store.rpc('rp_ai_finish', dict(p_user=user_id, p_id=request_id,
                         p_success=True, p_usage=records, p_result=result)).execute().data
        if settled['status'] != 'succeeded':
            raise RuntimeError('AI task settlement did not succeed.')
        return settled['result']
    finally:
        _usage.reset(token)


def run_ai_task(task, operation):
    if not managed_ai():
        return operation()
    import streamlit as st
    from supabase import create_client
    public_client = st.session_state.get('_account_client')
    if public_client is None:
        raise ValueError('Please sign in before using AI.')
    user = public_client.auth.get_user().user
    if not user or user.id != st.session_state.get('_account_id'):
        raise ValueError('Please sign in again.')
    config = json.loads((Path(__file__).resolve().parents[1] / 'deploy/public_config.json').read_text())
    secret = server_setting('SUPABASE_SERVICE_ROLE_KEY')
    if not secret:
        raise RuntimeError('AI credit service is not configured.')
    # This privileged client stays inside the server call. Never use it for user documents.
    server = create_client(config['SUPABASE_URL'], secret)
    from postgrest.exceptions import APIError
    from .i18n import t
    try:
        return execute_task(server, user.id, task, operation,
                            int(server_setting('AI_DAILY_REQUEST_LIMIT') or '50'))
    except APIError as exc:
        messages = {
            'NO_CREDITS': '免费体验已用完。购买服务尚未开放，你仍可免费查看历史、保存笔记和打卡。',
            'TASK_PENDING': '上一项任务仍在处理中，请在使用记录中查看状态，不要重复提交。',
            'RATE_LIMIT': '本小时尝试次数较多，请稍后再试。',
            'DAILY_LIMIT': '今日 AI 服务额度已用完，请明天再试。',
            'VERIFIED_ACCOUNT_REQUIRED': '请先完成邮箱验证后再使用 AI。',
        }
        message = messages.get(getattr(exc, 'message', ''), '额度处理尚未确认，请查看使用记录；若显示处理中，请勿重复提交。')
        raise ValueError(t(message)) from None


def task_notice():
    if managed_ai():
        import streamlit as st
        from .i18n import t
        st.caption(t('你的账号享有不限次使用权限。本次内容将发送给平台配置的 AI 服务商。') if unlimited_account() else t('本次 AI 任务使用 1 次额度。失败不扣次；首次验证邮箱赠送 1 次。所选内容将发送给平台配置的 AI 服务商。'))


def unlimited_account():
    """Display entitlement from the user's RLS-protected wallet; never grant it here."""
    if not managed_ai():
        return False
    import streamlit as st
    client = st.session_state.get('_account_client')
    if client is None:
        return False
    rows = client.table('rp_ai_wallets').select('unlimited').eq('user_id', st.session_state['_account_id']).execute().data
    return bool(rows and rows[0]['unlimited'])


def render_credits():
    import streamlit as st
    from .i18n import t, label
    st.subheader(t('AI 使用额度'))
    client = st.session_state['_account_client']
    user_id = st.session_state['_account_id']
    try:
        wallet = client.table('rp_ai_wallets').select('remaining,unlimited').eq('user_id', user_id).execute().data
        runs = client.table('rp_ai_runs').select('id,task,status,created_at,result').eq('user_id', user_id).order('created_at', desc=True).limit(30).execute().data
    except Exception:
        st.error(t('额度服务尚未就绪，请稍后再试。'))
        return
    st.metric(t('剩余次数'), t('不限次') if wallet and wallet[0]['unlimited'] else wallet[0]['remaining'] if wallet else 1)
    st.caption(t('你的账号享有不限次使用权限。本次内容将发送给平台配置的 AI 服务商。') if wallet and wallet[0]['unlimited'] else t('首次验证邮箱赠送 1 次。查看历史、保存笔记和学习打卡始终免费。'))
    st.caption(t('微信支付尚未开放，当前不收款。次数包价格将在成本验证后公布。'))
    with st.expander(t('最近使用记录')):
        if not runs:
            st.caption(t('还没有使用记录。'))
        for row in runs:
            st.write(f"{row['created_at'][:16]} · {label({'jd':'岗位分析','notes':'学习笔记','document':'资料问答'}[row['task']])} · {label({'pending':'处理中','succeeded':'已完成','failed':'失败，未扣次'}[row['status']])}")
            if row['status'] == 'succeeded':
                st.download_button(t('下载结果'), json.dumps(row['result'], ensure_ascii=False, indent=2),
                                   file_name='rolepath-result.json', mime='application/json', key='ai_result_' + row['id'])
