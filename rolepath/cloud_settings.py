import os
from urllib.parse import urlparse

def cloud_mode():
    return os.getenv('ROLEPATH_CLOUD') == '1'

def server_setting(name):
    """Read server secrets only; never return them to a widget or browser component."""
    value = os.getenv(name, '')
    if value:
        return value
    if cloud_mode():
        import streamlit as st
        try:
            return str(st.secrets.get(name, ''))
        except FileNotFoundError:
            return ''
    return ''

def managed_ai():
    return cloud_mode() and server_setting('ROLEPATH_AI_MODE') == 'managed'

def model_setting(name):
    if not cloud_mode():
        return os.getenv(name, '')
    if managed_ai():
        return server_setting(name)
    import streamlit as st
    return st.session_state.get('visitor_' + name, '')

def valid_model_endpoint(value):
    p = urlparse(value)
    return p.scheme == 'https' and (not p.username) and (not p.password) and (not p.port) and (not p.query) and (not p.fragment) and (p.path.rstrip('/') == '/compatible-mode/v1') and (p.hostname in ('dashscope.aliyuncs.com', 'dashscope-intl.aliyuncs.com') or (p.hostname or '').endswith('.maas.aliyuncs.com'))

def render_model_settings():
    from .i18n import t as tr
    if managed_ai():
        from .credits import render_credits
        render_credits()
        return
    import streamlit as st
    configured = bool(model_setting('LLM_API_KEY'))
    st.caption(tr('AI：已配置（当前会话）') if configured else tr('AI：当前会话尚未配置'))
    with st.expander(tr('我的 AI 配置')):
        st.caption(tr('模型调用费用由你的 API 账户承担。Key 仅保留在本次登录会话，不写入数据库；退出后清除。点击分析时，所选文字会发送给阿里云百炼。'))
        with st.form('visitor_model_form'):
            key = st.text_input(tr('百炼 API Key'), type='password', placeholder=tr('已保存；留空保留当前 Key') if configured else tr('填写你自己的 API Key'), key='ui_c90909bc9819')
            endpoint = st.text_input(tr('OpenAI 兼容地址'), value=model_setting('LLM_BASE_URL') or 'https://dashscope.aliyuncs.com/compatible-mode/v1', key='ui_a07e09d0ca7f')
            model = st.text_input(tr('模型名称'), value=model_setting('LLM_MODEL') or 'qwen-plus', key='ui_15af5bc2b434')
            submit = st.form_submit_button(tr('应用配置'))
        if submit:
            key = key.strip() or model_setting('LLM_API_KEY')
            if not valid_model_endpoint(endpoint.strip()) or not key.strip() or (not model.strip()):
                st.error(tr('请填写有效的百炼地址、Key 和模型名称。'))
            else:
                st.session_state.update({'visitor_LLM_API_KEY': key.strip(), 'visitor_LLM_BASE_URL': endpoint.strip(), 'visitor_LLM_MODEL': model.strip(), 'visitor_LLM_ENABLE_THINKING': 'false'})
                st.success(tr('配置已应用到当前会话。'))
