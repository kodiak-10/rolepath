from email.message import EmailMessage
import pytest
from rolepath import payment_notifications as n


def test_notification_contains_order_only_and_uses_tls(monkeypatch):
    values={'PAYMENT_SMTP_HOST':'smtp.yeah.net','PAYMENT_SMTP_PORT':'465','PAYMENT_SMTP_USERNAME':'sender@example.test','PAYMENT_SMTP_PASSWORD':'secret','PAYMENT_SMTP_FROM':'sender@example.test'}
    monkeypatch.setattr(n,'server_setting',lambda name:values.get(name,''))
    calls=[]
    class SMTP:
        def __init__(self,host,port,timeout,context):calls.append(('connect',host,port,bool(context)))
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def login(self,user,password):calls.append(('login',user,password))
        def send_message(self,msg):calls.append(('sent',msg))
    monkeypatch.setattr(n.smtplib,'SMTP_SSL',SMTP)
    n.send_review_alert('RP-123456ABCDEF','owner@example.test')
    msg=calls[-1][1]
    assert isinstance(msg,EmailMessage)
    assert msg['To']=='owner@example.test'
    assert 'RP-123456ABCDEF' in msg.get_content()
    assert '不代表已确认到账' in msg.get_content()
    assert calls[0][1:]==('smtp.yeah.net',465,True)


def test_invalid_order_and_missing_smtp_fail_without_sending(monkeypatch):
    monkeypatch.setattr(n,'server_setting',lambda name:'')
    monkeypatch.setattr(n.smtplib,'SMTP_SSL',lambda *a,**k:pytest.fail('Unexpected SMTP connection'))
    with pytest.raises(ValueError):n.send_review_alert('bad-order','owner@example.test')
    with pytest.raises(RuntimeError):n.send_review_alert('RP-123456ABCDEF','owner@example.test')


def test_refused_recipient_is_not_reported_as_delivered(monkeypatch):
    values={'PAYMENT_SMTP_HOST':'smtp.yeah.net','PAYMENT_SMTP_PORT':'465','PAYMENT_SMTP_USERNAME':'sender','PAYMENT_SMTP_PASSWORD':'secret','PAYMENT_SMTP_FROM':'sender@example.test'}
    monkeypatch.setattr(n,'server_setting',lambda name:values.get(name,''))
    class SMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def login(self,*args):pass
        def send_message(self,msg):return {'owner@example.test':(550,b'refused')}
    monkeypatch.setattr(n.smtplib,'SMTP_SSL',SMTP)
    with pytest.raises(RuntimeError,match='refused'):
        n.send_review_alert('RP-123456ABCDEF','owner@example.test')
