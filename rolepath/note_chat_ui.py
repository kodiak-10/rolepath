"""A single, focused conversation window for saved notes and original photos."""
import streamlit as st
from .i18n import t as tr, language
from .db import connect
from .knowledge import get_documents
from .image_text import is_image, IMAGE_TYPES
from .notes import note_inventory, summarize_notes, save_report
from .photo_notes import analyze_photos
from .llm import is_configured
from .credits import run_ai_task
from .cloud_settings import managed_ai, cloud_mode
from .credits import unlimited_account
from .resume_review import RESUME_TYPES, extract_resume, review_resume


def open_note_chat(parsed=None):
    st.session_state['_membership_checkout_open'] = False
    st.session_state['_note_chat_open'] = True


def render_open_note_chat(parsed=None):
    if st.session_state.get('_note_chat_open'):
        def close():
            st.session_state['_note_chat_open'] = False
        st.dialog(tr('学习助手'), width='large', on_dismiss=close)(render_note_chat)(parsed)


def render_note_chat(parsed=None):
    if cloud_mode():
        from .browser_session import refresh_action_session
        refresh_action_session()
    con = connect()
    try:
        docs = [dict(d) for d in get_documents(con) if not is_image(d['filename'])]
        labels = {d['id']: d['filename'] for d in docs}
        tools, reset = st.columns([5, 1])
        with tools, st.popover(tr('选择资料'), icon=':material/attach_file:'):
            selected = st.multiselect(tr('本次使用的笔记'), list(labels), default=list(labels),
                                      format_func=labels.get, key='dialog_note_sources')
            st.caption(tr('照片或简历可通过输入框旁的加号添加；每次最多 4 张照片或一份简历。'))
        if reset.button(tr('新对话'), key='dialog_note_reset', use_container_width=True):
            for key in ('workspace_note_chat', 'workspace_note_photos', 'workspace_photo_result', 'workspace_photo_pending', 'workspace_photo_error', 'workspace_resume_text', 'workspace_resume_name'):
                st.session_state.pop(key, None)
        scope = tuple(sorted(selected))
        if st.session_state.get('workspace_note_scope') != scope:
            st.session_state['workspace_note_scope'] = scope
            st.session_state.pop('workspace_note_chat', None)
        chat = st.session_state.setdefault('workspace_note_chat', [])
        photos = st.session_state.get('workspace_note_photos', [])
        resume_text = st.session_state.get('workspace_resume_text', '')
        if photos:
            st.caption(tr('正在使用照片：{0}', '、'.join(name for name, _ in photos)))
        elif resume_text:
            st.caption(tr('正在使用简历：{0}', st.session_state.get('workspace_resume_name', '')))
        else:
            st.caption(tr('已选择 {0} 份资料', len(selected)))
        with st.container(height=300, border=False, key='note_chat_messages'):
            if not chat:
                st.markdown('<div class="rp-chat-empty"><div class="rp-chat-glyph">✦</div><h3>' + tr('从一个问题开始。') + '</h3><p>' + tr('分析简历、解释笔记，或一起练一道题。') + '</p></div>', unsafe_allow_html=True)
            for turn in chat:
                with st.chat_message(turn['role']):
                    st.write(turn['content'])
        limit = len(chat) >= 6
        if limit:
            st.caption(tr('本轮已完成 3 次回答，开始新对话可继续。'))
        if not is_configured():
            st.caption(tr('AI 服务尚未配置，仍可上传和查看资料。'))
        st.caption(tr('你的账号享有不限次使用权限。本次内容将发送给平台配置的 AI 服务商。') if managed_ai() and unlimited_account() else tr('发送即将本次资料和问题交给已配置的千问服务。每次回答用 1 次额度，失败不扣次。') if managed_ai()
                   else tr('发送时，所选资料和问题会交给你配置的模型服务。'))
        st.caption(tr('可上传简历 PDF、DOCX、TXT 或照片。发送后内容会交给 AI 服务商；分析简历文档时会同时发送当前岗位描述，原文件不自动保存。'))
        if managed_ai():
            st.caption(tr('AI 分析结果会保存在你的账号中。'))
        prompt = st.chat_input(tr('问点什么，或添加简历、笔记…'), key='workspace_note_prompt',
                               accept_file='multiple', file_type=list(IMAGE_TYPES)+list(RESUME_TYPES), max_chars=3000,
                               disabled=not is_configured() or limit)
        retry = False
        if st.session_state.get('workspace_photo_error'):
            st.error(tr('本次回答未完成：{0}', st.session_state['workspace_photo_error']))
            st.caption(tr('照片和问题已保留在当前会话，可以修改问题后发送，或重试；不会自动重复调用 AI。'))
            st.write(tr('上次问题：') + st.session_state.get('workspace_photo_pending', ''))
            retry = st.button(tr('重试这次照片请求'), key='retry_photo_request', disabled=limit or not is_configured())
        if prompt or retry:
            text = st.session_state['workspace_photo_pending'] if retry else prompt if isinstance(prompt, str) else prompt.text
            incoming = [] if retry or isinstance(prompt, str) else [(f.name, f.getvalue()) for f in prompt.files]
            if incoming:
                image_files = [f for f in incoming if is_image(f[0])]
                document_files = [f for f in incoming if not is_image(f[0])]
                if document_files and (image_files or len(document_files) != 1):
                    st.error(tr('请单独上传一份简历，或只上传照片。'))
                    return
                if document_files:
                    try:
                        resume_text = extract_resume(*document_files[0])
                    except ValueError as exc:
                        st.error(str(exc))
                        return
                    st.session_state.pop('workspace_photo_result', None)
                    st.session_state['workspace_resume_text'] = resume_text
                    st.session_state['workspace_resume_name'] = document_files[0][0]
                    st.session_state.pop('workspace_note_photos', None)
                    st.session_state.pop('workspace_photo_error', None)
                    chat.clear()
                    photos = []
                else:
                    st.session_state.pop('workspace_photo_result', None)
                    st.session_state.pop('workspace_photo_error', None)
                    st.session_state.pop('workspace_resume_text', None)
                    st.session_state.pop('workspace_resume_name', None)
                    resume_text = ''
                    chat.clear()
            task_photos = (incoming if incoming and is_image(incoming[0][0]) else []) or photos
            if task_photos:
                # Keep the user's request even when the provider fails. No automatic retry.
                st.session_state['workspace_note_photos'] = task_photos
                st.session_state['workspace_photo_pending'] = text
            try:
                with st.spinner(tr('正在思考…')):
                    if task_photos:
                        result = run_ai_task('notes', lambda: analyze_photos(task_photos, text, language(), history=chat.copy()))
                        answer = result['answer']
                        st.session_state['workspace_photo_result'] = result
                        st.session_state['workspace_note_photos'] = task_photos
                    elif resume_text:
                        result = run_ai_task('notes', lambda: review_resume(resume_text, text, parsed['raw'] if parsed else '', chat.copy(), language()))
                        answer = result['answer']
                    else:
                        rows, _ = note_inventory(con, selected, [])
                        if not rows:
                            raise ValueError(tr('请先选择资料，或通过加号添加照片。'))
                        def analyze_and_save():
                            result = summarize_notes(rows, parsed['raw'] if parsed else '', text, chat.copy())
                            save_report(con, result)
                            return result
                        result = run_ai_task('notes', analyze_and_save)
                        answer = '\n\n'.join(i['kind'] + '：' + i['text'] for i in result['items'])
                    chat.extend([{'role':'user','content':text or (tr('请分析我的简历并提出修改建议。') if resume_text else tr('帮我整理这些笔记。'))},
                                 {'role':'assistant','content':answer}])
                    st.session_state.pop('workspace_photo_error', None)
                    st.session_state.pop('workspace_photo_pending', None)
                st.rerun()
            except Exception as exc:
                if task_photos:
                    st.session_state['workspace_photo_error'] = str(exc)
                    st.rerun()
                else:
                    st.error(tr('本次回答未完成：{0}', exc))
        photo_result = st.session_state.get('workspace_photo_result')
        if photo_result:
            with st.expander(tr('核对并保存 AI 学习记录')):
                from .photo_notes_ui import render_photo_review
                render_photo_review(con, photo_result)
        if cloud_mode():
            from .browser_session import sync_action_session
            sync_action_session()
    finally:
        con.close()
