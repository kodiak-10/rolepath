"""Conversation and attachment controls in the Goudan panel."""
import logging

import streamlit as st

from .cloud_settings import managed_ai
from .credits import run_ai_task
from .db import connect
from .i18n import t as tr, language
from .image_text import is_image, IMAGE_TYPES
from .knowledge import get_documents
from .notes import note_inventory, summarize_notes, save_report
from .photo_notes import analyze_photos
from .resume_review import RESUME_TYPES, extract_resume, review_resume


def open_note_chat():
    st.session_state['_doll_open'] = True
    st.session_state['_doll_select_notes'] = True


def _clear_request(state):
    for key in ('workspace_photo_error', 'workspace_photo_pending', '_doll_error', '_doll_pending'):
        state.pop(key, None)


def _clear_sources(state):
    for key in ('workspace_note_photos', 'workspace_photo_result', 'workspace_resume_text', 'workspace_resume_name'):
        state.pop(key, None)


def render_note_chat(parsed, picked, configured, tutor):
    con = connect()
    try:
        labels = {d['id']: d['filename'] for d in get_documents(con) if not is_image(d['filename'])}
        _render_conversation(con, labels, parsed, picked, configured, tutor)
    finally:
        con.close()


def _render_conversation(con, labels, parsed, picked, configured, tutor):
    state = st.session_state
    if 'workspace_note_chat' not in state:
        state['workspace_note_chat'] = state.pop('_doll_chat', [])
    chat = state['workspace_note_chat']
    previous = state.get('workspace_note_scope', ())
    select_notes = state.pop('_doll_select_notes', False)
    selected = list(labels) if select_notes else [note for note in previous if note in labels]

    tools, reset = st.columns([1, 1])
    start_new = reset.button(tr('新对话'), key='dialog_note_reset', use_container_width=True)
    if start_new:
        chat.clear()
        _clear_sources(state)
        _clear_request(state)
        selected = []
    if select_notes or start_new:
        state['dialog_note_sources'] = selected
    elif 'dialog_note_sources' in state:
        stale = state['dialog_note_sources']
        if any(note not in labels for note in stale):
            state['dialog_note_sources'] = [note for note in stale if note in labels]
    with tools, st.popover(tr('选择资料'), icon=':material/attach_file:', use_container_width=True):
        selected = st.multiselect(tr('本次使用的笔记'), list(labels),
                                  default=None if 'dialog_note_sources' in state else selected,
                                  format_func=labels.get, key='dialog_note_sources')
        st.caption(tr('照片或简历可通过输入框旁的加号添加；每次最多 4 张照片或一份简历。'))
        st.caption(tr('可上传简历 PDF、DOCX、TXT 或照片。发送后内容会交给 AI 服务商；分析简历文档时会同时发送当前岗位描述，原文件不自动保存。'))
    scope = tuple(sorted(selected))
    has_attachment = state.get('workspace_note_photos') or state.get('workspace_resume_text')
    if scope != previous or (select_notes and scope and has_attachment):
        chat.clear()
        _clear_sources(state)
        _clear_request(state)
    state['workspace_note_scope'] = scope

    photos = state.get('workspace_note_photos', [])
    resume_text = state.get('workspace_resume_text', '')
    if photos:
        st.caption(tr('正在使用照片：{0}', '、'.join(name for name, _ in photos)))
    elif resume_text:
        st.caption(tr('正在使用简历：{0}', state.get('workspace_resume_name', '')))
    elif selected:
        st.caption(tr('已选择 {0} 份资料', len(selected)))
    with st.container(height=235, border=False, key='doll_messages'):
        if not chat:
            st.markdown(tr('分析简历、解释笔记，或一起练一道题。'))
        for turn in chat:
            with st.chat_message(turn['role']):
                st.write(turn['content'])
    if not configured:
        st.info(tr('AI 暂时不可用，请稍后重试'))
    if managed_ai():
        st.caption(tr('本次内容将发送给服务端配置的 AI 服务商（参赛版免费）。'))

    retry = False
    pending = None
    if state.get('workspace_photo_error'):
        st.error(tr('AI 暂时不可用，请稍后重试'))
        pending = state['workspace_photo_pending']
        st.caption(tr('照片和问题已保留在当前会话，可以修改问题后发送，或重试；不会自动重复调用 AI。'))
        if pending:
            st.write(tr('上次问题：') + pending)
        retry = st.button(tr('重试这次照片请求'), key='retry_photo_request', disabled=not configured)
    elif state.get('_doll_error'):
        st.error(tr('AI 暂时不可用，请稍后重试'))
        pending = state['_doll_pending']
        st.caption(tr('问题已保留，可重试；不会自动重复调用 AI。'))
        retry = st.button(tr('重试这次提问'), key='doll_retry', disabled=not configured)

    st.caption(tr('简历和图片会在发送后交给 AI 分析。'))
    prompt = st.chat_input(tr('问狗蛋…'), key='doll_prompt', accept_file='multiple',
                           file_type=[*IMAGE_TYPES, *RESUME_TYPES], max_chars=3000, disabled=not configured)
    if configured and (prompt or picked or retry):
        question = pending if retry else picked
        incoming = []
        if prompt:
            question = prompt.text
            incoming = [(file.name, file.getvalue()) for file in prompt.files]
        if incoming:
            images = [item for item in incoming if is_image(item[0])]
            if (images and len(images) != len(incoming)) or (not images and len(incoming) != 1):
                st.error(tr('请单独上传一份简历，或只上传照片。'))
                return
            if len(images) > 4:
                st.error(tr('每次最多 4 张照片，请减少选择。'))
                return
            try:
                resume_text = '' if images else extract_resume(*incoming[0])
            except ValueError as exc:
                st.error(tr(str(exc)))
                return
            _clear_sources(state)
            _clear_request(state)
            chat.clear()
            photos = images
            if photos:
                state['workspace_note_photos'] = photos
            else:
                state['workspace_resume_text'] = resume_text
                state['workspace_resume_name'] = incoming[0][0]

        if len(chat) >= 6 and (photos or resume_text or selected):
            st.info(tr('本轮已完成 3 次回答，开始新对话可继续。'))
        else:
            question = (question or '').strip()
            if photos and not question:
                question = tr('请分析这些图片，指出看不清的地方。')
            try:
                with st.spinner(tr('正在思考…')):
                    answer = _answer(con, parsed, tutor, selected, photos, resume_text, question, chat)
                chat.extend([{'role': 'user', 'content': question or tr('分析附件')},
                             {'role': 'assistant', 'content': answer}])
                _clear_request(state)
            except Exception as exc:
                logging.getLogger(__name__).warning('Goudan request failed: %s', type(exc).__name__)
                if photos:
                    state['workspace_photo_error'] = True
                    state['workspace_photo_pending'] = question
                else:
                    state['_doll_error'] = True
                    state['_doll_pending'] = question
            st.rerun()

    photo_result = state.get('workspace_photo_result')
    if photo_result:
        with st.expander(tr('核对并保存 AI 学习记录')):
            from .photo_notes_ui import render_photo_review
            render_photo_review(con, photo_result)


def _answer(con, parsed, tutor, selected, photos, resume_text, question, chat):
    jd = parsed['raw'] if parsed else ''
    if photos:
        result = run_ai_task('notes', lambda: analyze_photos(photos, question, language(), history=chat.copy()))
        st.session_state['workspace_photo_result'] = result
    elif resume_text:
        result = run_ai_task('notes', lambda: review_resume(resume_text, question, jd, chat.copy(), language()))
    elif selected:
        rows, _ = note_inventory(con, selected, [])

        def analyze_and_save():
            report = summarize_notes(rows, jd, question, chat.copy())
            save_report(con, report)
            return report

        report = run_ai_task('notes', analyze_and_save)
        return '\n\n'.join(i['kind'] + '：' + i['text'] for i in report['items'])
    else:
        result = run_ai_task('tutor', lambda: tutor(question, chat[-6:]))
    return result['answer']
