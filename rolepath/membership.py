"""Monthly access and manually verified WeChat collection orders. No auto-renewals."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
PRICE_FEN=1290
PRODUCT='monthly_1290_unlimited_v1'


def config():
    return json.loads((ROOT/'deploy/membership.json').read_text())


def access_state(wallet, now=None):
    now=now or datetime.now(timezone.utc)
    end=wallet.get('member_until')
    until=datetime.fromisoformat(end.replace('Z','+00:00')) if end else None
    if until and until.tzinfo is None:
        raise ValueError('Membership expiry must include a timezone.')
    permanent=bool(wallet.get('unlimited'))
    active=permanent or bool(until and until>now)
    return dict(active=active,permanent=permanent,until=until,remaining=wallet.get('remaining',1))


def verified_actor():
    client=st.session_state.get('_account_client')
    user=client.auth.get_user().user if client else None
    if not user or user.id!=st.session_state.get('_account_id'):
        raise PermissionError('Please sign in again.')
    return client,user.id


def wallet_for(client,user_id):
    rows=client.table('rp_ai_wallets').select('remaining,unlimited,member_until').eq('user_id',user_id).execute().data
    return rows[0] if rows else dict(remaining=1,unlimited=False,member_until=None)


def orders_for(client,user_id):
    return client.table('rp_membership_orders').select('*').eq('user_id',user_id).order('created_at',desc=True).limit(20).execute().data


def create_order():
    if not config()['sales_enabled']:
        raise RuntimeError('MEMBERSHIP_SALES_CLOSED')
    client,_=verified_actor()
    return client.rpc('rp_membership_create_order',{}).execute().data


def submit_order(order_id,paid_at,reference):
    client,_=verified_actor()
    if paid_at.tzinfo is None or not 4<=len(reference.strip())<=80:
        raise ValueError('INVALID_PAYMENT_REFERENCE')
    return client.rpc('rp_membership_submit_order',dict(p_id=order_id,p_paid_at=paid_at.isoformat(),p_reference=reference.strip())).execute().data


def notify_payment_review(order_code):
    from .payment_notifications import send_review_alert
    send_review_alert(order_code, config()['support_email'])


def is_admin(client):
    return client.rpc('rp_membership_is_admin',{}).execute().data is True


def admin_client():
    client,user_id=verified_actor()
    if not is_admin(client):
        raise PermissionError('ADMIN_REQUIRED')
    from supabase import create_client
    from .cloud_settings import server_setting
    public=json.loads((ROOT/'deploy/public_config.json').read_text())
    secret=server_setting('SUPABASE_SERVICE_ROLE_KEY')
    if not secret:
        raise RuntimeError('Membership administration is not configured.')
    return create_client(public['SUPABASE_URL'],secret),user_id


def review_orders(query=''):
    client,user_id=admin_client()
    return client.rpc('rp_membership_admin_orders',dict(p_admin=user_id,p_query=query.strip())).execute().data


def received_fen(text):
    try:
        amount=Decimal(text)
    except (InvalidOperation,TypeError,ValueError):
        raise ValueError('PAYMENT_AMOUNT_MISMATCH') from None
    if not amount.is_finite() or amount*100 != (amount*100).to_integral_value() or amount*100!=PRICE_FEN:
        raise ValueError('PAYMENT_AMOUNT_MISMATCH')
    return int(amount*100)


def review_order(order_id,approve,amount,note):
    client,user_id=admin_client()
    if not isinstance(approve,bool):
        raise ValueError('INVALID_REVIEW')
    fen=received_fen(amount) if approve else 0
    return client.rpc('rp_membership_review_order',dict(p_admin=user_id,p_id=order_id,p_approve=approve,p_received_fen=fen,p_note=note.strip())).execute().data
