from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import pytest
import streamlit as st
from rolepath import membership as m

NOW=datetime(2026,10,27,tzinfo=timezone.utc)

def test_expiry_uses_absolute_time_and_expires_at_boundary():
    end='2026-10-27T08:00:00+08:00'
    assert m.access_state(dict(member_until=end,remaining=0),NOW-timedelta(seconds=1))['active']
    assert not m.access_state(dict(member_until=end,remaining=0),NOW)['active']
    assert not m.access_state(dict(member_until=end,remaining=0),NOW+timedelta(seconds=1))['active']

def test_permanent_access_does_not_depend_on_expiry():
    assert m.access_state(dict(unlimited=True,member_until='2020-01-01T00:00:00Z'),NOW)['active']
    assert not m.access_state({},NOW)['active']
    with pytest.raises(ValueError):m.access_state(dict(member_until='2026-10-27T12:00:00'),NOW)

@pytest.mark.parametrize('amount',['0','12.899','13','NaN','Infinity','wrong',None])
def test_wrong_receipt_amount_cannot_activate(amount):
    with pytest.raises(ValueError,match='PAYMENT_AMOUNT_MISMATCH'):m.received_fen(amount)

@pytest.mark.parametrize('amount',['12.9','12.90','12.900',' 12.90 '])
def test_exact_receipt_amount(amount):
    assert m.received_fen(amount)==1290

def test_review_uses_verified_server_identity_and_exact_amount(monkeypatch):
    calls=[]
    class Client:
        def rpc(self,name,args):
            calls.append((name,args));return SimpleNamespace(execute=lambda:SimpleNamespace(data={'status':'approved'}))
    monkeypatch.setattr(m,'admin_client',lambda:(Client(),'verified-reviewer'))
    m.review_order('order',True,'12.9',' checked ')
    assert calls==[('rp_membership_review_order',dict(p_admin='verified-reviewer',p_id='order',p_approve=True,p_received_fen=1290,p_note='checked'))]
    with pytest.raises(ValueError):m.review_order('order','true','12.9','')

def test_unsigned_or_mismatched_account_cannot_use_admin_service(monkeypatch):
    st.session_state['_account_id']='account-a'
    st.session_state['_account_client']=SimpleNamespace(auth=SimpleNamespace(get_user=lambda:SimpleNamespace(user=SimpleNamespace(id='account-b'))))
    with pytest.raises(PermissionError):m.admin_client()
    st.session_state.pop('_account_client');st.session_state.pop('_account_id')

def test_closed_sales_never_create_order(monkeypatch):
    monkeypatch.setattr(m,'config',lambda:dict(sales_enabled=False))
    monkeypatch.setattr(m,'verified_actor',lambda:pytest.fail('Must not call the database when sales are closed'))
    with pytest.raises(RuntimeError,match='MEMBERSHIP_SALES_CLOSED'):m.create_order()

def checkout_app(monkeypatch,orders):
    from rolepath import browser_session
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(browser_session,'refresh_action_session',lambda:None)
    monkeypatch.setattr(browser_session,'sync_action_session',lambda:None)
    monkeypatch.setattr(m,'verified_actor',lambda:(None,'test-user'))
    monkeypatch.setattr(m,'orders_for',lambda *_:orders)
    monkeypatch.setattr(m,'config',lambda:dict(sales_enabled=True,support_email='support@example.invalid'))
    return AppTest.from_string("""
import streamlit as st
from rolepath.membership_ui import render_open_checkout
st.session_state.setdefault('_language','zh')
st.session_state.setdefault('_membership_checkout_open',True)
st.session_state.setdefault('_membership_preview',False)
render_open_checkout()
""").run()

def test_checkout_survives_order_creation_and_full_rerun(monkeypatch):
    orders=[]
    def create():
        order=dict(id='test-order',code='RP-TEST',status='awaiting_payment')
        orders.append(order);return order
    monkeypatch.setattr(m,'create_order',create)
    at=checkout_app(monkeypatch,orders)
    at.button(key='member_create_order').click().run()
    assert not at.exception
    assert at.session_state['_membership_order_id']=='test-order'
    assert at.text_input[0].label=='付款备注或微信账单号后 6 位'
    assert len(orders)==1

def test_checkout_submit_is_not_activation_and_approval_displays_expiry(monkeypatch):
    order=dict(id='test-order',code='RP-TEST',status='awaiting_payment')
    def submit(*_):order['status']='submitted'
    monkeypatch.setattr(m,'submit_order',submit)
    at=checkout_app(monkeypatch,[order])
    at.text_input[0].input('123456')
    at.checkbox[0].check()
    at.button[-1].click().run()
    assert not at.exception
    assert '等待人工核对' in at.success[0].value
    order.update(status='approved',period_end='2026-11-27T00:00:00Z')
    at.button(key='member_refresh_order').click().run()
    assert not at.exception
    assert '2026-11-27 08:00' in at.success[0].value
    assert not at.button

def test_checkout_preview_cannot_submit_payment(monkeypatch):
    at=checkout_app(monkeypatch,[])
    at.session_state['_membership_preview']=True;at.run()
    assert not at.exception
    assert at.button[-1].disabled
    assert any('管理账号预览' in info.value for info in at.info)
