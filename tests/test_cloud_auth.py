import base64
import json
import pytest
from rolepath.cloud_auth import validate_public_config


def key_for(role):
    payload=base64.urlsafe_b64encode(json.dumps({'role':role}).encode()).decode().rstrip('=')
    return 'header.'+payload+'.signature'


@pytest.mark.parametrize('key',['sb_publishable_test',key_for('anon')])
def test_public_keys_allowed(key):
    validate_public_config('https://project.supabase.co', key)


@pytest.mark.parametrize('key',['sb_secret_test',key_for('service_role'),key_for('authenticated'),'invalid'])
def test_privileged_and_invalid_keys_rejected(key):
    with pytest.raises(ValueError):
        validate_public_config('https://project.supabase.co',key)


@pytest.mark.parametrize('url',['http://project.supabase.co','https://supabase.co.evil.com','https://localhost','https://x.supabase.co/?x=1','https://user@x.supabase.co'])
def test_invalid_auth_destination_rejected(url):
    with pytest.raises(ValueError):
        validate_public_config(url,'sb_publishable_test')


def test_streamlit_client_rotates_tokens_only_during_browser_sync(monkeypatch):
    import supabase
    from rolepath.cloud_auth import new_client
    captured={}
    def create(url,key,options):
        captured['options']=options
        return object()
    monkeypatch.setattr(supabase,'create_client',create)
    new_client('https://example.supabase.co','sb_publishable_test')
    assert captured['options'].auto_refresh_token is False
    assert captured['options'].persist_session is False
