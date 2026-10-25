"""Explicit image consent, one task for reading + answering, editable transcription."""
import hashlib
import streamlit as st
from .i18n import t, language
from .image_text import IMAGE_TYPES
from .llm import is_configured
from .credits import run_ai_task, task_notice
from .photo_notes import analyze_photos
from .knowledge import save_document


def render_photo_notes(con):
    st.markdown('### ' + t('照片笔记助手'))
    st.caption(t('直接查看原始照片，按你的指令解释、总结或出题。读图和回答合计使用 1 次额度；不会先用传统 OCR 转成文字。'))
    photos = st.file_uploader(t('选择笔记照片（每次 1–4 张）'), type=list(IMAGE_TYPES), accept_multiple_files=True, key='photo_note_files')
    instruction = st.text_area(t('你希望怎样处理这些照片？'), key='photo_note_instruction', max_chars=3000,
                               placeholder=t('例如：解释这页 SQL 笔记，指出看不清的地方，再出两道练习题。'))
    consent = st.checkbox(t('同意将本次所选照片和指令发送给已配置的千问服务进行识别与回答。'), key='photo_note_consent')
    task_notice()
    if st.button(t('看图并回答'), key='photo_note_submit', disabled=not photos or not consent or not is_configured()):
        try:
            if len(photos) > 4:
                raise ValueError(t('每次最多 4 张照片，请减少选择。'))
            with st.spinner(t('正在查看照片并回答…')):
                report = run_ai_task('notes', lambda: analyze_photos([(f.name, f.getvalue()) for f in photos], instruction, language()))
            st.session_state['photo_note_result'] = report
        except Exception as exc:
            st.error(t('看图任务未完成：{0}', exc))
    report = st.session_state.get('photo_note_result')
    if not report:
        return
    st.caption(t('这份回答来自原始照片。转录仍可能有误，请对照照片核对；标为无法辨认的内容没有补猜。'))
    for item in report['items']:
        st.write(item['text'])
        source = next(p for p in report['pages'] if p['ref'] == item['source_ref'])
        st.caption(source['filename'])
    st.markdown('#### ' + t('核对并保存文字'))
    st.caption(t('确认后的文字才会加入笔记库。保存不消耗 AI 次数；原始照片不长期保存。'))
    edits = []
    for page in report['pages']:
        if page['uncertain']:
            st.warning(page['filename'] + '：' + '；'.join(page['uncertain']))
        key = hashlib.sha256((report['created_at'] + page['ref'] + page['transcript']).encode()).hexdigest()[:20]
        edits.append((page['filename'], st.text_area(page['filename'], value=page['transcript'], key='photo_text_' + key)))
    confirmed = st.checkbox(t('我已对照照片核对并修正文字。'), key='photo_confirm_' + hashlib.sha256(report['created_at'].encode()).hexdigest()[:12])
    if st.button(t('保存核对后的笔记'), disabled=not confirmed, key='photo_note_save'):
        try:
            for name, text in edits:
                if len(text.strip()) < 15:
                    raise ValueError(t('可保存文字不足，请先核对或补充。'))
            for name, text in edits:
                save_document(con, name + '.verified.md', [(1, text)])
            st.success(t('已保存核对后的文字；不会覆盖旧笔记。'))
        except Exception as exc:
            st.error(str(exc))
