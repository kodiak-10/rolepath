"""Send a minimal payment-review alert through the site's SMTP account."""
from email.message import EmailMessage
import re
import smtplib
import ssl

from .cloud_settings import server_setting


def send_review_alert(order_code, recipient):
    if not re.fullmatch(r'RP-[A-F0-9]{12}', order_code):
        raise ValueError('Invalid order number')
    host = server_setting('PAYMENT_SMTP_HOST')
    port = server_setting('PAYMENT_SMTP_PORT')
    username = server_setting('PAYMENT_SMTP_USERNAME')
    password = server_setting('PAYMENT_SMTP_PASSWORD')
    sender = server_setting('PAYMENT_SMTP_FROM')
    if not all((host, port, username, password, sender, recipient)):
        raise RuntimeError('Payment notification email is not configured')
    if host != 'smtp.yeah.net' or port != '465':
        raise ValueError('Unsupported payment notification SMTP settings')
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = 'RolePath：有付款申请待审核'
    msg.set_content(f'订单 {order_code} 已提交付款信息。请登录 RolePath 的付款审核页面，并在微信账单核对到账后处理。\n\n此邮件不代表已确认到账。')
    with smtplib.SMTP_SSL(host, int(port), timeout=20, context=ssl.create_default_context()) as smtp:
        smtp.login(username, password)
        refused = smtp.send_message(msg)
        if refused:
            raise RuntimeError('Payment notification recipient was refused')
