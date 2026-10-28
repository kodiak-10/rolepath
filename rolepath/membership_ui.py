"""A small monthly-plan checkout and an isolated payment review workspace."""
from base64 import b64encode
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from . import membership as member
from .i18n import t as tr,label

ZONE=ZoneInfo('Asia/Shanghai')
STATUSES={'awaiting_payment':'待付款','submitted':'待人工核对','needs_info':'需补充信息','approved':'已开通'}


def display_time(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(ZONE).strftime('%Y-%m-%d %H:%M')


def error_message(exc):
    message=getattr(exc,'message',str(exc))
    messages={
        'MEMBERSHIP_SALES_CLOSED':tr('月卡暂未开放收款，请勿转账。'),
        'INVALID_PAYMENT_REFERENCE':tr('请填写付款备注或微信账单号后 6 位。'),
        'INVALID_PAYMENT_TIME':tr('请核对付款时间，不能填写未来时间或订单创建前的付款。'),
        'PAYMENT_AMOUNT_MISMATCH':tr('实收金额必须为 ¥12.90，不能凭用户自述开通。'),
        'REVIEW_NOTE_REQUIRED':tr('请说明需要用户补充的信息。'),
        'ADMIN_REQUIRED':tr('你没有付款审核权限。'),
        'ORDER_NOT_SUBMITTED':tr('订单尚未提交付款信息，请刷新订单状态。'),
        'ORDER_NOT_FOUND':tr('未找到这份订单，请刷新后重试。'),
        'PERMANENT_ACCESS':tr('你的账号已享有不限次权限，无需购买。'),
    }
    return messages.get(message,tr('订单状态尚未确认，请刷新查看，不要重复付款。'))


def support(order=None):
    email=member.config()['support_email']
    st.caption(tr('联系支持：{0}。请提供订单编号，方便核对。',email))
    st.link_button(tr('邮件联系支持'),'mailto:'+email+'?subject=RolePath%20'+(order['code'] if order else 'Plus'))


def offer():
    st.markdown('<div class="rp-plus-heading"><span>ROLEPATH PLUS</span><h2>¥12.90<small>'+tr('/ 月')+'</small></h2><p>'+tr('AI 不限次数，让学习连续发生。')+'</p></div>',unsafe_allow_html=True)
    st.write(tr('岗位深度分析 · 照片总结与测试题 · 笔记分析和资料问答'))
    st.caption(tr('人工确认到账后生效，有效期为一个自然月；不自动扣款、不自动续费。'))
    st.caption(tr('到期后，已保存的笔记、计划和打卡仍可查看。'))


def render_checkout(preview=False):
    from .browser_session import refresh_action_session,sync_action_session
    refresh_action_session()
    offer()
    settings=member.config()
    if preview:
        st.info(tr('管理账号预览，不创建订单，也不提交付款信息。'))
        order=dict(code='RP-XXXXXXXXXXXX',status='awaiting_payment')
    else:
        client,user_id=member.verified_actor()
        orders=member.orders_for(client,user_id)
        selected=st.session_state.get('_membership_order_id')
        order=next((o for o in orders if o['id']==selected),None) if selected else None
        if order is None:
            order=next((o for o in orders if o['status'] in ('awaiting_payment','submitted','needs_info')),None)
        if order:
            st.session_state['_membership_order_id']=order['id']
        if not order:
            if not settings['sales_enabled']:
                st.info(tr('月卡暂未开放收款，请勿转账。'))
            if st.button(tr('生成付款订单'),type='primary',key='member_create_order',disabled=not settings['sales_enabled'],use_container_width=True):
                try:
                    order=member.create_order()
                    st.session_state['_membership_order_id']=order['id']
                    st.rerun()
                except Exception as exc:
                    st.error(error_message(exc))
            support();sync_action_session();return
    if order['status']=='approved':
        st.success(tr('会员已开通，有效至 {0}',display_time(order['period_end'])))
        st.code(order['code'],language=None)
        support(order);sync_action_session();return
    if order['status']=='submitted':
        st.success(tr('付款信息已提交，正在等待人工核对。请勿重复付款。'))
        st.code(order['code'],language=None)
        if st.session_state.get('_payment_alert_failed') == order['id']:
            st.warning(tr('提醒邮件发送失败，请联系支持并提供订单编号；请勿重复付款。'))
            if st.button(tr('重试发送提醒'),key='retry_payment_alert'):
                try:
                    member.notify_payment_review(order['code'])
                except Exception:
                    st.warning(tr('提醒邮件发送失败，请联系支持并提供订单编号；请勿重复付款。'))
                else:
                    st.session_state.pop('_payment_alert_failed',None)
                    st.rerun()
        if st.button(tr('刷新订单状态'),key='member_refresh_order'):
            st.rerun()
        support(order);sync_action_session();return
    if order['status']=='needs_info':
        st.warning(order.get('review_note') or tr('请核对并补充付款信息。'))
    qr,details=st.columns([1,1.3],gap='large')
    with qr:
        encoded=b64encode((member.ROOT/'assets/wechat-collection.jpg').read_bytes()).decode('ascii')
        st.markdown('<div class="rp-payment-qr"><img alt="'+tr('微信收款二维码')+'" src="data:image/jpeg;base64,'+encoded+'"></div>',unsafe_allow_html=True)
        st.caption(tr('请使用微信支付 ¥12.90；请核对收款人尾字“文”。'))
        st.caption(tr('请作者喝杯奶茶'))
    with details:
        st.markdown('**'+tr('订单编号')+'**')
        st.code(order['code'],language=None)
        st.write(tr('请在付款备注中填写订单编号。完成支付后，在下方提交付款信息。'))
        st.caption(tr('这是个人收款码，提交付款信息不等于已到账，也不会自动开通。'))
    now=datetime.now(ZONE)
    with st.form('member_payment_submission'):
        ref=st.text_input(tr('付款备注或微信账单号后 6 位'),max_chars=80)
        day,col_time=st.columns(2)
        paid_day=day.date_input(tr('付款日期'),value=now.date(),max_value=now.date())
        paid_time=col_time.time_input(tr('付款时间'),value=now.time().replace(second=0,microsecond=0),step=60)
        confirmed=st.checkbox(tr('我已支付 ¥12.90，并核对了订单编号。'))
        submitted=st.form_submit_button(tr('我已付款，提交审核'),type='primary',disabled=preview or not settings['sales_enabled'],use_container_width=True)
    if submitted:
        if not confirmed:
            st.error(tr('付款完成并核对信息后，再提交审核。'))
        else:
            try:
                member.submit_order(order['id'],datetime.combine(paid_day,paid_time,tzinfo=ZONE),ref)
                try:
                    member.notify_payment_review(order['code'])
                except Exception:
                    st.session_state['_payment_alert_failed']=order['id']
                st.rerun()
            except Exception as exc:
                st.error(error_message(exc))
    support(order if not preview else None)
    sync_action_session()


def open_checkout(preview=False):
    st.session_state['_note_chat_open']=False
    st.session_state['_membership_checkout_open']=True
    st.session_state['_membership_preview']=preview
    st.session_state.pop('_membership_order_id',None)
    st.rerun()


def render_open_checkout():
    if st.session_state.get('_membership_checkout_open'):
        def close():
            st.session_state['_membership_checkout_open']=False
        st.dialog(tr('开通 RolePath Plus'),width='large',on_dismiss=close)(render_checkout)(st.session_state['_membership_preview'])


def render_my_membership(client,user_id,state):
    st.subheader(tr('我的会员'))
    offer()
    if not member.config()['sales_enabled']:
        st.info(tr('月卡暂未开放收款，请勿转账。'))
    if state['permanent']:
        st.success(tr('你的账号已享有长期不限次权限，无需购买。'))
    elif state['active']:
        st.success(tr('Plus 已开通 · 有效至 {0}',state['until'].astimezone(ZONE).strftime('%Y-%m-%d %H:%M')))
    else:
        st.caption(tr('免费体验剩余 {0} 次；会员到期后不会自动扣费。',state['remaining']))
        if state['until']:
            st.caption(tr('上次会员已于 {0} 到期。',state['until'].astimezone(ZONE).strftime('%Y-%m-%d %H:%M')))
    if st.button(tr('预览付费窗口') if state['permanent'] else tr('续费月卡') if state['active'] else tr('开通月卡'),type='primary',key='open_member_checkout'):
        open_checkout(state['permanent'])
    orders=member.orders_for(client,user_id)
    if orders:
        with st.expander(tr('我的订单')):
            for order in orders:
                st.write(order['code']+' · '+label(STATUSES[order['status']])+' · ¥12.90')
                st.caption(display_time(order['created_at']))
                if order['status']=='approved':
                    st.caption(tr('服务有效期：{0} 至 {1}',display_time(order['period_start']),display_time(order['period_end'])))
                elif order['status']=='needs_info':
                    st.warning(order.get('review_note') or tr('请核对并补充付款信息。'))
    with st.expander(tr('AI 使用记录')):
        runs=client.table('rp_ai_runs').select('id,task,status,created_at,result').eq('user_id',user_id).order('created_at',desc=True).limit(30).execute().data
        if not runs:st.caption(tr('还没有使用记录。'))
        for row in runs:
            st.write(display_time(row['created_at'])+' · '+label({'jd':'岗位分析','notes':'学习笔记','document':'资料问答','resources':'资源检索'}[row['task']])+' · '+label({'pending':'处理中','succeeded':'已完成','failed':'失败，未扣次'}[row['status']]))
            if row['status']=='succeeded':
                import json
                st.download_button(tr('下载结果'),json.dumps(row['result'],ensure_ascii=False,indent=2),file_name='rolepath-result.json',mime='application/json',key='ai_result_'+row['id'])
    support()


def render_payment_review():
    st.subheader(tr('付款审核'))
    st.caption(tr('仅审核账号可见。请先在微信账单核对真实到账，再开通会员；重复确认同一订单不会重复延长。'))
    if st.button(tr('发送测试提醒'),key='test_payment_alert'):
        try:
            member.notify_payment_review('RP-000000000000')
        except Exception:
            st.error(tr('测试提醒发送失败，请检查发信配置。'))
        else:
            st.success(tr('测试提醒已由邮件服务器接收，请检查收件箱。'))
    query=st.text_input(tr('搜索订单编号或邮箱'),key='payment_review_search',max_chars=100)
    try:
        orders=member.review_orders(query)
    except Exception as exc:
        st.error(error_message(exc));return
    st.caption(tr('最多展示最近 100 条匹配订单。'))
    if not orders:st.info(tr('没有待处理的订单。'))
    for order in orders:
        with st.expander(order['code']+' · '+order['email']+' · '+label(STATUSES[order['status']])):
            st.write(tr('应付金额：¥12.90'))
            if order.get('paid_at'):st.write(tr('用户填写的付款时间：{0}',display_time(order['paid_at'])))
            st.write(tr('付款信息：{0}',order.get('payment_reference') or '—'))
            if order['status']!='submitted':continue
            with st.form('review_'+order['id']):
                amount=st.text_input(tr('微信账单实收金额（元）'),value='12.90')
                note=st.text_input(tr('审核说明（补充信息时必填）'),max_chars=300)
                checked=st.checkbox(tr('我已在微信账单核对该订单真实到账 ¥12.90。'))
                approve=st.form_submit_button(tr('确认到账并开通会员'),type='primary')
                ask=st.form_submit_button(tr('请用户补充信息'))
            if approve or ask:
                if approve and not checked:
                    st.error(tr('请先核对微信真实到账，不能凭用户提交的信息开通。'));continue
                try:
                    member.review_order(order['id'],approve,amount,note)
                    st.success(tr('审核结果已保存。'));st.rerun()
                except Exception as exc:
                    st.error(error_message(exc))


def render_membership():
    try:
        client,user_id=member.verified_actor()
        state=member.access_state(member.wallet_for(client,user_id))
        administrator=member.is_admin(client)
    except Exception:
        st.error(tr('会员服务尚未就绪，请稍后再试。'));return
    if administrator:
        mine,review=st.tabs([tr('我的会员'),tr('付款审核')])
        with mine:render_my_membership(client,user_id,state)
        with review:render_payment_review()
    else:
        render_my_membership(client,user_id,state)
