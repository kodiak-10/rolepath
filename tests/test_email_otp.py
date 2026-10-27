from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rolepath.cloud_auth import send_email_code, verify_email_code

@pytest.fixture(autouse=True)
def browser_bridge(monkeypatch):
    from rolepath import browser_session
    monkeypatch.setattr(browser_session, 'restore_browser_session', lambda client: {'available':False})
    monkeypatch.setattr(browser_session, 'queue_session', lambda session: None)


def test_send_uses_signup_capable_otp_without_password():
    client = Mock()
    assert send_email_code(client, ' student@example.com ') == 'student@example.com'
    client.auth.sign_in_with_otp.assert_called_once_with({
        'email': 'student@example.com', 'options': {'should_create_user': True},
    })


def test_invalid_email_does_not_send():
    client = Mock()
    with pytest.raises(ValueError):
        send_email_code(client, 'not an email')
    client.auth.sign_in_with_otp.assert_not_called()


def test_mail_failure_is_not_reported_as_sent():
    client = Mock()
    client.auth.sign_in_with_otp.side_effect = RuntimeError('SMTP unavailable')
    with pytest.raises(RuntimeError):
        send_email_code(client, 'student@example.com')


def test_verify_binds_code_to_requested_email():
    client = Mock()
    result = SimpleNamespace(session=object(), user=object())
    client.auth.verify_otp.return_value = result
    assert verify_email_code(client, 'student@example.com', ' 123456 ') is result
    client.auth.verify_otp.assert_called_once_with({
        'email': 'student@example.com', 'token': '123456', 'type': 'email',
    })


def test_missing_session_is_not_success():
    client = Mock()
    client.auth.verify_otp.return_value = SimpleNamespace(session=None, user=None)
    with pytest.raises(ValueError):
        verify_email_code(client, 'student@example.com', '123456')


def test_invalid_code_does_not_request_login():
    client = Mock()
    with pytest.raises(ValueError):
        verify_email_code(client, 'student@example.com', 'abcdef')
    client.auth.verify_otp.assert_not_called()

@pytest.mark.parametrize('failure', [TimeoutError('timeout'), RuntimeError('mail error')])
def test_delivery_error_still_allows_server_verification(monkeypatch, failure):
    from streamlit.testing.v1 import AppTest
    from rolepath import cloud_auth
    client = Mock()
    client.auth.get_session.return_value = None
    client.auth.sign_in_with_otp.side_effect = failure
    monkeypatch.setattr(cloud_auth, 'new_client', lambda *a: client)
    at = AppTest.from_string('from rolepath.cloud_auth import require_login\nrequire_login()').run()
    at.text_input[0].input('student@example.com')
    next(b for b in at.button if b.label == 'Send code').click().run()
    assert not at.exception
    assert at.warning and not at.success
    assert any(t.label == 'Email verification code' for t in at.text_input)
    client.auth.verify_otp.return_value = SimpleNamespace(session=None, user=None)
    at.text_input[0].input('123456')
    next(b for b in at.button if b.label == 'Verify and sign in').click().run()
    client.auth.verify_otp.assert_called_once_with({'email':'student@example.com','token':'123456','type':'email'})
    assert at.error  # Invalid verification never grants access.


def test_existing_code_can_be_verified_without_resending(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from rolepath import cloud_auth
    client = Mock()
    client.auth.get_session.return_value = None
    monkeypatch.setattr(cloud_auth, 'new_client', lambda *a: client)
    at = AppTest.from_string('from rolepath.cloud_auth import require_login\nrequire_login()').run()
    at.text_input[0].input('student@example.com')
    next(b for b in at.button if b.label == 'Already have a code?').click().run()
    assert not at.exception
    client.auth.sign_in_with_otp.assert_not_called()
    assert any(t.label == 'Email verification code' for t in at.text_input)
    client.auth.verify_otp.return_value = SimpleNamespace(session=object(), user=object())
    client.auth.verify_otp.side_effect = lambda *a: (setattr(client.auth.get_session,'return_value',object()) or SimpleNamespace(session=object(),user=object()))
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id='student-id',email='student@example.com'))
    at.text_input[0].input('123456')
    next(b for b in at.button if b.label == 'Verify and sign in').click().run()
    assert not at.exception
    assert at.session_state['_account_id'] == 'student-id'


def test_rate_limit_is_distinguished():
    from supabase_auth.errors import AuthApiError
    from rolepath.cloud_auth import request_email_code
    client=Mock()
    client.auth.sign_in_with_otp.side_effect=AuthApiError('rate limit',429,'over_email_send_rate_limit')
    state={}
    request_email_code(client,'student@example.com',state)
    assert '频繁' in state['_otp_notice'][1]
