from types import SimpleNamespace
import pytest
from rolepath.credits import execute_task, record_usage, _usage

class Ledger:
    def __init__(self):
        self.balance = 1
        self.unlimited = False
        self.runs = {}
        self.settle_error = False
    def rpc(self, name, p):
        def execute():
            if name == 'rp_ai_reserve':
                rid=p['p_id']
                if rid in self.runs:
                    return SimpleNamespace(data={**self.runs[rid], 'execute':False})
                if self.balance < 1 and not self.unlimited:
                    raise ValueError('NO_CREDITS')
                if not self.unlimited:
                    self.balance-=1
                self.runs[rid]={'status':'pending','execute':True,'charged':not self.unlimited}
                return SimpleNamespace(data=self.runs[rid])
            if self.settle_error:
                raise ConnectionError('settlement unavailable')
            row=self.runs[p['p_id']]
            if row['status']=='pending':
                row.update(status='succeeded' if p['p_success'] else 'failed', result=p['p_result'],usage=p['p_usage'])
                if not p['p_success'] and row['charged']:
                    self.balance+=1
            return SimpleNamespace(data=row)
        return SimpleNamespace(execute=execute)

def test_success_is_charged_once_and_replay_returns_saved_result():
    ledger=Ledger()
    def operation():
        record_usage({'prompt_tokens':100,'completion_tokens':20})
        return {'answer':'saved'}
    assert execute_task(ledger,'u','jd',operation,50,'one')=={'answer':'saved'}
    assert execute_task(ledger,'u','jd',lambda:pytest.fail('replayed'),50,'one')=={'answer':'saved'}
    assert ledger.balance==0
    assert ledger.runs['one']['usage'][0]['prompt_tokens']==100
    assert _usage.get() is None

def test_validation_failure_refunds_and_keeps_provider_usage():
    ledger=Ledger()
    def operation():
        record_usage({'total_tokens':123})
        raise ValueError('invalid citation')
    with pytest.raises(ValueError,match='invalid citation'):
        execute_task(ledger,'u','notes',operation,50,'one')
    assert ledger.balance==1
    assert ledger.runs['one']['usage']==[{'total_tokens':123}]
    assert ledger.runs['one']['status']=='failed'
    assert _usage.get() is None

def test_empty_balance_never_calls_provider():
    ledger=Ledger(); ledger.balance=0
    with pytest.raises(ValueError,match='NO_CREDITS'):
        execute_task(ledger,'u','jd',lambda:pytest.fail('no credit'),50)

def test_pending_replay_never_calls_provider():
    ledger=Ledger();ledger.runs['one']={'status':'pending'}
    with pytest.raises(ValueError,match='already running'):
        execute_task(ledger,'u','jd',lambda:pytest.fail('duplicate'),50,'one')

def test_settlement_outage_does_not_refund_a_possibly_committed_result():
    ledger=Ledger();ledger.settle_error=True
    with pytest.raises(ConnectionError):
        execute_task(ledger,'u','jd',lambda:{'answer':'ok'},50,'one')
    assert ledger.balance==0
    assert ledger.runs['one']['status']=='pending'
    assert _usage.get() is None

def test_unserializable_result_is_refunded():
    ledger=Ledger()
    with pytest.raises(TypeError):
        execute_task(ledger,'u','jd',lambda:{'bad':set()},50,'one')
    assert ledger.balance==1

def test_managed_mode_never_uses_visitor_key(monkeypatch):
    from rolepath import cloud_settings
    monkeypatch.setenv('ROLEPATH_CLOUD','1')
    monkeypatch.setenv('ROLEPATH_AI_MODE','managed')
    monkeypatch.setenv('LLM_API_KEY','server-test-key')
    assert cloud_settings.model_setting('LLM_API_KEY')=='server-test-key'

def test_managed_provider_call_requires_reservation(monkeypatch):
    from rolepath import llm
    monkeypatch.setenv('ROLEPATH_CLOUD','1')
    monkeypatch.setenv('ROLEPATH_AI_MODE','managed')
    with pytest.raises(RuntimeError,match='reserved task'):
        llm._message('x','y')


def test_unlimited_account_runs_with_zero_balance_and_keeps_history():
    ledger=Ledger();ledger.balance=0;ledger.unlimited=True
    for i in range(7):
        assert execute_task(ledger,'owner','jd',lambda:{'answer':'ok'},1,str(i))=={'answer':'ok'}
    assert ledger.balance==0
    assert len(ledger.runs)==7 and all(not r['charged'] for r in ledger.runs.values())


def test_unlimited_failure_does_not_create_extra_credits():
    ledger=Ledger();ledger.balance=0;ledger.unlimited=True
    def fail(): raise ValueError('provider failed')
    with pytest.raises(ValueError,match='provider failed'):
        execute_task(ledger,'owner','notes',fail,1,'failed')
    assert ledger.balance==0 and ledger.runs['failed']['status']=='failed'


def test_entitlement_migration_keeps_write_permissions_on_server():
    from pathlib import Path
    sql=(Path(__file__).resolve().parents[1]/'deploy/account_entitlements.sql').read_text()
    assert 'unlimited boolean not null default false' in sql
    assert 'not w.unlimited and w.remaining < 1' in sql
    assert 'p_success and r.charged' in sql
    assert 'from public,anon,authenticated' in sql
    assert 'to authenticated' not in sql
