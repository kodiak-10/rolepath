"""Enter Community Cloud's supported presentation mode before loading account data."""
import streamlit as st
import streamlit.components.v2 as components
from .cloud_settings import cloud_mode

_redirect = components.component('clean_presentation', js='''
export default function({data}) {
  window.top.location.replace(data.url);
}
''')


def ensure_clean_presentation():
    if not cloud_mode() or st.context.is_embedded:
        return
    locale = 'zh' if st.query_params.get('lang') == 'zh' else 'en'
    _redirect(data={'url':'https://rolepath-kodiak.streamlit.app/?embed=true&lang='+locale}, key='clean_presentation', height=0)
    st.stop()
