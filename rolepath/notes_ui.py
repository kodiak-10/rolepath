"""A quiet material library. Conversation opens in its own window."""
from html import escape
import streamlit as st
from .i18n import t as tr
from .db import connect
from .knowledge import pages_from_upload, save_document, get_documents, get_chunks, delete_document
from .notes import reports, export_report
from .image_text import is_image
from .note_chat_ui import open_note_chat


def open_document(doc):
    @st.dialog(doc['filename'], width='large')
    def view():
        con = connect()
        try:
            if is_image(doc['filename']):
                st.warning(tr('这是旧版自动识别的文字，请对照原图核对。'))
            for row in get_chunks(con):
                if row['document_id'] == doc['id']:
                    st.text(row['content'])
            with st.popover(tr('管理资料')):
                confirm = st.checkbox(tr('确认删除这份资料及其关联分析。'), key='delete_confirm_' + doc['id'])
                if st.button(tr('删除资料'), key='delete_note_' + doc['id'], disabled=not confirm):
                    delete_document(con, doc['id'])
                    st.rerun()
        finally:
            con.close()
    view()


def open_reports():
    @st.dialog(tr('历史分析'), width='large')
    def view():
        con = connect()
        try:
            saved = reports(con)
            if not saved:
                st.caption(tr('还没有分析记录，开始一次对话后会显示在这里。'))
            for rid, report in saved:
                with st.expander(report.get('instruction') or report['created_at']):
                    st.caption(report['created_at'])
                    for item in report['items']:
                        st.write(item['text'])
                        with st.expander(tr('查看出处')):
                            source = next(r for r in report['sources'] if r['id'] == item['source_id'])
                            st.caption(source['filename'])
                            st.text(item['quote'])
                    st.download_button(tr('下载这份汇总'), export_report(report), file_name='rolepath-notes.md',
                                       mime='text/markdown', key='download_' + rid)
        finally:
            con.close()
    view()


def render_notes(parsed):
    st.markdown('<div class="rp-library-heading"><div class="rp-kicker">YOUR LEARNING LIBRARY</div><h1>' + tr('学习笔记') + '</h1><p>' + tr('把零散的学习，变成自己的积累。') + '</p></div>', unsafe_allow_html=True)
    chat, upload, history, space = st.columns([1.25, 1.1, 1.1, 2.5])
    if chat.button(tr('与笔记对话'), type='primary', icon=':material/chat_bubble_outline:', key='open_note_chat', use_container_width=True):
        open_note_chat(parsed)
    con = connect()
    try:
        with upload, st.popover(tr('添加资料'), icon=':material/add:', use_container_width=True):
            st.caption(tr('文档保存在资料库；照片在对话窗口中添加。'))
            files = st.file_uploader(tr('上传文档'), type=['txt','md','pdf'], accept_multiple_files=True, key='study_note_upload')
            if st.button(tr('保存资料'), key='save_study_note', disabled=not files, use_container_width=True):
                for file in files:
                    try:
                        save_document(con, file.name, pages_from_upload(file))
                        st.success(tr('已保存：{0}', file.name))
                    except Exception as exc:
                        st.error(str(exc))
        if history.button(tr('历史分析'), icon=':material/history:', key='open_note_reports', use_container_width=True):
            open_reports()
        docs = [dict(d) for d in get_documents(con)]
        st.write('')
        if not docs:
            st.markdown('<div class="rp-library-empty"><span>↗</span><h3>' + tr('你的知识，从这里开始。') + '</h3><p>' + tr('添加一份文档，或打开对话发送照片。') + '</p></div>', unsafe_allow_html=True)
        for doc in docs:
            with st.container(key='note_row_' + doc['id']):
                title, action = st.columns([7, 1])
                with title:
                    st.markdown('<div class="rp-note-name">' + escape(doc['filename']) + '</div>', unsafe_allow_html=True)
                    st.caption(tr('旧照片文字 · 待核对') if is_image(doc['filename']) else tr('已保存的资料'))
                if action.button(tr('打开'), key='view_note_' + doc['id'], use_container_width=True):
                    open_document(doc)
    finally:
        con.close()
