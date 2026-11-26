"""Contest edition is free: no purchase entry, price, payment copy or QR anywhere."""
import ast
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from rolepath import db

ROOT = Path(__file__).resolve().parents[1]


def test_no_checkout_entry_or_qr_asset_in_contest_source():
    assert not (ROOT / 'assets/wechat-collection.jpg').exists()
    for p in [ROOT / 'app.py', *(ROOT / 'rolepath').glob('*.py')]:
        source = p.read_text()
        assert 'wechat-collection' not in source, p
        assert 'render_open_checkout' not in source, p
        assert 'render_membership' not in source, p
    from rolepath import membership_ui
    assert not [n for n in dir(membership_ui) if not n.startswith('__')]


def test_catalog_has_no_price_or_payment_copy():
    catalog = json.loads((ROOT / 'rolepath/translations.json').read_text())
    for key, value in catalog.items():
        for text in (key, value):
            assert '¥' not in text and '12.90' not in text, text
            assert '收款' not in text and '付款' not in text and '月卡' not in text, text


def test_local_pages_show_no_membership_or_payment_ui(monkeypatch, tmp_path):
    monkeypatch.setenv('ROLEPATH_CLOUD', '0')
    monkeypatch.setattr(db, 'DB_FILE', str(tmp_path / 'free.sqlite3'))
    at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=45).run()
    assert not at.exception
    for page in ['我的空间', '岗位分析', '课程与题目', '学习计划', '学习任务', '学习笔记', '历史记录']:
        at.session_state['page'] = page
        at.run()
        assert not at.exception, page
        rendered = ' '.join(el.value for el in at.markdown) + ' '.join(el.value for el in at.caption)
        rendered += ' '.join(b.label for b in at.button)
        for word in ('会员', '月卡', '¥', '收款', '付款', '升级'):
            assert word not in rendered, (page, word)


def test_managed_wallet_is_disabled_in_contest(monkeypatch):
    monkeypatch.setenv('ROLEPATH_CLOUD', '1')
    monkeypatch.setenv('ROLEPATH_AI_MODE', 'managed')
    from rolepath.cloud_settings import managed_ai
    from rolepath.credits import run_ai_task
    assert managed_ai() is False
    assert run_ai_task('tutor', lambda: {'answer': 'free'}) == {'answer': 'free'}