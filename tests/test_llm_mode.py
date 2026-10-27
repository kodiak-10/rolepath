from types import SimpleNamespace
import pytest
from rolepath import llm


def test_thinking_setting_is_explicit(monkeypatch):
    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='ok'))],usage=None)
    monkeypatch.setattr(llm,'client',lambda:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setenv('LLM_MODEL','test')
    monkeypatch.setenv('LLM_ENABLE_THINKING','false')
    assert llm._message('data','system')[0]=='ok'
    assert captured['extra_body']=={'enable_thinking':False}
    monkeypatch.delenv('LLM_ENABLE_THINKING')
    captured.clear()
    llm._message('data','system')
    assert 'extra_body' not in captured


@pytest.mark.parametrize('reason,content',[('length','partial'),('stop','')])
def test_incomplete_model_output_is_rejected(monkeypatch,reason,content):
    response=SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason,message=SimpleNamespace(content=content))],usage=None)
    monkeypatch.setattr(llm,'client',lambda:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:response))))
    monkeypatch.setenv('LLM_MODEL','test')
    monkeypatch.delenv('LLM_ENABLE_THINKING',raising=False)
    with pytest.raises(ValueError):llm._message('data','system')


def test_generation_timeout_and_no_hidden_retry(monkeypatch):
    import openai
    monkeypatch.setenv('LLM_API_KEY', 'test')
    monkeypatch.setenv('LLM_MODEL', 'test')
    options = {}
    monkeypatch.setattr(openai, 'OpenAI', lambda **kw: options.update(kw))
    llm.client()
    assert options['timeout'].read == 180
    assert options['timeout'].connect == 10
    assert options['max_retries'] == 0
