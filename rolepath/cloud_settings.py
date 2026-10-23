import os
from urllib.parse import urlparse


def cloud_mode():
    return os.getenv('ROLEPATH_CLOUD') == '1'


def model_setting(name):
    if not cloud_mode():
        return os.getenv(name, '')
    import streamlit as st
    return st.session_state.get('visitor_'+name, '')


def valid_model_endpoint(value):
    p=urlparse(value)
    return (p.scheme=='https' and not p.username and not p.password and not p.port and not p.query and not p.fragment
            and p.path.rstrip('/')=='/compatible-mode/v1'
            and (p.hostname in ('dashscope.aliyuncs.com','dashscope-intl.aliyuncs.com') or (p.hostname or '').endswith('.maas.aliyuncs.com')))


def render_model_settings():
    import streamlit as st
    configured = bool(model_setting('LLM_API_KEY'))
    st.caption('AI：已配置（当前会话）' if configured else 'AI：当前会话尚未配置')
    with st.expander('我的 AI 配置'):
        st.caption('模型调用费用由你的 API 账户承担。Key 仅保留在本次登录会话，不写入数据库；退出后清除。点击分析时，所选文字会发送给阿里云百炼。')
        with st.form('visitor_model_form'):
            key=st.text_input('百炼 API Key',type='password', placeholder='已保存；留空保留当前 Key' if configured else '填写你自己的 API Key')
            endpoint=st.text_input('OpenAI 兼容地址',value=model_setting('LLM_BASE_URL') or 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            model=st.text_input('模型名称',value=model_setting('LLM_MODEL') or 'qwen-plus')
            submit=st.form_submit_button('应用配置')
        if submit:
            key = key.strip() or model_setting('LLM_API_KEY')
            if not valid_model_endpoint(endpoint.strip()) or not key.strip() or not model.strip():
                st.error('请填写有效的百炼地址、Key 和模型名称。')
            else:
                st.session_state.update({'visitor_LLM_API_KEY':key.strip(),'visitor_LLM_BASE_URL':endpoint.strip(), 'visitor_LLM_MODEL':model.strip(),'visitor_LLM_ENABLE_THINKING':'false'})
                st.success('配置已应用到当前会话。')
