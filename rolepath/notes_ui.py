from .i18n import t as tr, label, table, formatter
import streamlit as st
from .image_text import UPLOAD_TYPES
from .db import connect
from .knowledge import pages_from_upload, save_document, get_documents
from .notes import note_inventory, summarize_notes, save_report, reports, export_report
from .llm import is_configured
from .cloud_settings import cloud_mode

def render_notes(parsed):
    st.subheader(tr('学习笔记 · 学习助手'))
    st.caption((tr('笔记保存到你的云端账户。') if cloud_mode() else tr('笔记保存在本机。')) + tr('可在资料问答检索和删除。点击发送指令后，所选笔记和当前 JD 将发送给配置的模型服务商。'))
    st.caption(tr('支持多张 PNG、JPG、HEIC/HEIF 照片，每张最多 5MB。照片在运行服务上识别文字；请先核对下方识别原文，再进行智能分析。手写和复杂排版可能有识别错误。'))
    upload = st.file_uploader(tr('上传学习笔记'), type=UPLOAD_TYPES, accept_multiple_files=True, key='study_note_upload')
    con = connect()
    try:
        if st.button(tr('保存学习笔记'), key='save_study_note', disabled=not upload):
            for file in upload:
                try:
                    with st.spinner(tr('正在读取 ') + file.name + '…'):
                        _, n = save_document(con, file.name, pages_from_upload(file))
                    st.success(file.name + (tr('：已保存。') if n else tr('：已存在，未重复保存。')))
                except Exception as exc:
                    st.error(file.name + tr('：未保存，') + str(exc))
        docs = get_documents(con)
        labels = {d['id']: d['filename'] + ' · ' + d['id'][:8] for d in docs}
        selected = st.multiselect(tr('选择要分析的笔记（可多选汇总）'), list(labels), default=list(labels), format_func=labels.get, key='notes_selected')
        requirements = parsed['requirements'] if parsed else []
        rows, assessed = note_inventory(con, selected, requirements)
        st.caption(tr('已选 {0} 份笔记、{1} 个片段。以下为词语提及检查，不是智能总结或能力评分。', len(selected), len(rows)))
        if assessed:
            st.dataframe(table([{'岗位技能': r['skill'], '笔记证据': r['status']} for r in assessed]), hide_index=True)
        if not is_configured():
            st.info(tr('尚未配置 LLM API Key：上传、保存、原文查看和检索可用；智能分析与跨笔记汇总尚不可用。'))
        st.info(tr('当前助手读取的是笔记文字，尚未直接理解原始照片。涉及手写公式、图表或识别不清的文字，请先核对；不能据此保证答案正确。'))
        scope = tuple(sorted(selected))
        if st.session_state.get('note_chat_scope') != scope:
            st.session_state.note_chat_scope = scope
            st.session_state.note_chat = []
        chat = st.session_state.setdefault('note_chat', [])
        if st.button(tr('开始新对话'), key='new_note_chat'):
            st.session_state.note_chat = []
            chat = []
        for turn in chat:
            with st.chat_message(turn['role']):
                st.write(turn['content'])
        instruction = st.text_area(tr('你想让助手做什么？'), key='note_instruction', max_chars=3000, placeholder=tr('例如：用简单的话解释这页笔记；根据笔记出三道题，先别给答案；检查我下面这段理解是否正确。留空则总结全部笔记。'))
        if len(chat) >= 6:
            st.info(tr('当前对话已完成 3 次回答，请开始新对话后继续。历史分析仍保存在下方。'))
        if st.button(tr('发送指令'), key='summarize_notes', disabled=not rows or not is_configured() or len(chat) >= 6):
            try:
                with st.spinner(tr('正在分析笔记并核对引用，多份笔记可能需要 1–3 分钟…')):
                    report = summarize_notes(rows, parsed['raw'] if parsed else '', instruction, chat.copy())
                    save_report(con, report)
                    answer = '\n\n'.join((item['kind'] + '：' + item['text'] for item in report['items']))
                    chat.extend([{'role': 'user', 'content': instruction.strip() or '总结全部所选笔记'}, {'role': 'assistant', 'content': answer}])
                with st.chat_message('assistant'):
                    st.write(answer)
                st.success(tr('分析已保存。请对照引用核查模型结论。'))
            except Exception as exc:
                from openai import APITimeoutError
                if isinstance(exc, APITimeoutError):
                    st.error(tr('模型服务响应超时，未生成或保存汇总；已上传的笔记仍在。请稍后重试。'))
                else:
                    st.error(tr('分析未完成：{0}', exc))
        with st.expander(tr('查看所选笔记原文与出处')):
            for row in rows:
                st.caption(tr('{0} · 第{1}页 · [{2}]', row['filename'], row['page'], row['id']))
                st.text(row['content'])
        st.markdown(tr('**已保存的分析与汇总**'))
        for rid, report in reports(con):
            with st.expander(report['created_at'] + ' · ' + str(len({r['document_id'] for r in report['sources']})) + tr(' 份笔记')):
                st.caption(tr('这是当时的笔记与 JD 分析记录，不代表当前岗位结论，也不代表能力已验证。'))
                st.write(tr('指令：') + report.get('instruction', '总结全部所选笔记'))
                if report.get('jd'):
                    with st.expander(tr('分析时使用的 JD')):
                        st.text(report['jd'])
                sources = {r['id']: r for r in report['sources']}
                for item in report['items']:
                    st.write(item['kind'] + '：' + item['text'])
                    source = sources[item['source_id']]
                    st.caption(tr('{0} · 第{1}页 · [{2}]', source['filename'], source['page'], source['id']))
                    st.text(tr('原文：') + item['quote'])
                st.download_button(tr('下载这份汇总'), export_report(report), file_name='学习笔记汇总.md', mime='text/markdown', key='download_' + rid)
    finally:
        con.close()
