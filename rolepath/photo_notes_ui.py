"""Review an AI photo response before adding it to the material library."""
import hashlib
import streamlit as st
from .i18n import t
from .knowledge import save_document


def render_photo_review(con, report):
    st.caption(t('这是根据照片生成的 AI 学习记录，不是系统验证过的逐字转录。请对照照片核对事实、公式和代码。'))
    st.caption(t('对应指令：') + report['instruction'])
    for source in report['sources']:
        st.caption(source['ref'] + ' · ' + source['filename'])
    key = hashlib.sha256((report['created_at'] + report['answer']).encode()).hexdigest()[:20]
    edited = st.text_area(t('AI 学习记录（可编辑）'), value=report['answer'], key='photo_answer_' + key, height=260)
    confirmed = st.checkbox(t('我已核对并修正这份 AI 学习记录。'), key='photo_answer_confirm_' + key)
    st.caption(t('保存不消耗 AI 次数；原始照片不长期保存。'))
    if st.button(t('保存这份学习记录'), disabled=not confirmed, key='photo_answer_save'):
        try:
            if len(edited.strip()) < 15:
                raise ValueError(t('可保存文字不足，请先核对或补充。'))
            sources = '\n'.join(s['ref'] + ' · ' + s['filename'] for s in report['sources'])
            content = '# AI 照片学习记录\n\n> AI 生成、用户核对；不是系统认证的逐字转录。\n\n' + '来源照片：\n' + sources + '\n\n用户指令：' + report['instruction'] + '\n\n学习记录：\n' + edited
            save_document(con, 'AI照片学习记录-' + key + '.md', [(1, content)])
            st.success(t('已保存学习记录，并标注 AI 来源；原始照片未长期保存。'))
        except Exception as exc:
            st.error(str(exc))
