"""Review and save a photo transcription inside the conversation window."""
import hashlib
import streamlit as st
from .i18n import t
from .knowledge import save_document


def render_photo_review(con, report):
    st.caption(t('这份回答来自原始照片。转录仍可能有误，请对照照片核对；标为无法辨认的内容没有补猜。'))
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
