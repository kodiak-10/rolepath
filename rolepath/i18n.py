"""Presentation-only translations. Stored content and identifiers stay unchanged."""
import json
from pathlib import Path
import streamlit as st

EN = json.loads(Path(__file__).with_name('translations.json').read_text())

def language():
    return st.session_state.get('_language', 'en')

def t(source, *args):
    text = EN[source] if language() == 'en' else source
    return text.format(*args) if args else text

def label(value, locale=None):
    """Known display labels only; source material is intentionally left intact."""
    return EN.get(value, value) if (locale or language()) == 'en' and isinstance(value, str) else value

def render_language_picker():
    if '_language' not in st.session_state:
        st.session_state['_language'] = 'zh' if st.query_params.get('lang') == 'zh' else 'en'
    def change():
        st.query_params['lang'] = st.session_state['_language']
    _, control = st.columns([5, 1.4])
    with control:
        st.selectbox('Language / 语言', ['en', 'zh'], key='_language',
                     format_func=lambda x: 'English' if x == 'en' else '简体中文', on_change=change)

def table(rows):
    """Translate column headings without rewriting user-provided cell values."""
    return [{label(k): v for k, v in row.items()} for row in rows]

def formatter():
    locale = language()
    return lambda value: label(value, locale)
