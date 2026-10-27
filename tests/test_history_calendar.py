from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
import pytest
from rolepath import db, knowledge, notes
from rolepath import history_ui as history


def seed(path):
    con=db.connect(path)
    pid=db.save_plan(con,'SQL 学习计划',[dict(id='task-1',title='GROUP BY 练习')],{})
    con.execute('UPDATE plans SET created_at=?',('2026-10-22 20:10:00',))
    docid,_=knowledge.save_document(con,'SQL笔记.md',[(1,'SQL GROUP BY 用于分组，COUNT 用于计算记录数量。')])
    con.execute('UPDATE documents SET created_at=?',('2026-10-22 20:30:00',))
    db.ensure_learning_log(con)
    con.execute('INSERT INTO learning_logs VALUES(?,?,?,?)',('task-1','2026-10-22',25,'复习分组统计'))
    report=dict(created_at='2026-10-22T21:00:00',instruction='总结学习',sources=[dict(r) for r in knowledge.get_chunks(con)],items=[dict(kind='总结',text='分组查询',source_id=knowledge.get_chunks(con)[0]['id'],quote='SQL GROUP BY 用于分组，COUNT 用于计算记录数量。')])
    notes.save_report(con,report);con.commit()
    return con,pid,docid


def test_real_saved_records_use_correct_dates_and_log_minutes(tmp_path):
    con,pid,docid=seed(tmp_path/'events.db')
    events=history.load_events(con);con.close()
    assert len(events)==4 and {e['kind'] for e in events}=={'plan','note','study','analysis'}
    by_kind={e['kind']:e for e in events}
    assert by_kind['plan']['day']==by_kind['note']['day']==date(2026,10,23)
    assert by_kind['analysis']['day']==by_kind['study']['day']==date(2026,10,22)
    assert by_kind['study']['payload']['minutes']==25
    assert by_kind['note']['time']=='04:30'


def test_offset_timestamps_and_naive_utc_cross_midnight():
    assert history.saved_time('2026-10-22T20:00:00+00:00').date()==date(2026,10,23)
    assert history.saved_time('2026-10-22 20:00:00').date()==date(2026,10,23)
    with pytest.raises(ValueError):history.saved_time('not-a-date')


def test_leap_month_has_real_day_markers_without_fabricated_records():
    day=date(2028,2,29)
    data=history.calendar_data(day.replace(day=1),day,[dict(day=day,kind='note')],day)
    assert len(data['days'])==42
    selected=next(d for d in data['days'] if d['selected'])
    assert selected['iso']=='2028-02-29' and selected['counts']=={'note':1}
    assert sum(sum(d['counts'].values()) for d in data['days'])==1
    assert [d['number'] for d in data['days'] if d['inMonth']]==list(range(1,30))


def test_calendar_month_navigation_and_date_selection():
    month=date(2026,1,1);today=date(2026,10,26)
    assert history.apply_calendar_action(dict(type='previous',month=month.isoformat()),month,today)==(date(2025,12,1),date(2025,12,1))
    assert history.apply_calendar_action(dict(type='today',month=month.isoformat()),month,today)==(date(2026,10,1),today)
    assert history.apply_calendar_action(dict(type='day',month=month.isoformat(),day='2026-01-22'),month,today)==(month,date(2026,1,22))
    with pytest.raises(ValueError):history.apply_calendar_action(dict(type='day',month=month.isoformat(),day='2027-01-22'),month,today)


def app(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    path=tmp_path/'ui.db'; con,pid,docid=seed(path);con.close()
    monkeypatch.setattr(db,'DB_FILE',str(path));monkeypatch.setenv('ROLEPATH_CLOUD','0')
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30)
    at.session_state['_language']='zh';at.session_state['page']='历史记录'
    at.session_state['_history_month']=date(2026,10,1);at.session_state['_history_day']=date(2026,10,23)
    return at,pid,docid


def test_date_click_filters_records_and_opens_the_actual_note(monkeypatch,tmp_path):
    at,pid,docid=app(monkeypatch,tmp_path)
    actions=[None,dict(type='day',month='2026-10-01',day='2026-10-22'),None]
    monkeypatch.setattr(history,'_calendar',lambda **kwargs:SimpleNamespace(action=actions.pop(0) if actions else None))
    at.run();assert not at.exception
    assert any(b.key=='history_note_'+docid for b in at.button)
    at.run();assert not at.exception
    assert at.session_state['_history_day']==date(2026,10,22)
    assert not any(b.key=='history_note_'+docid for b in at.button)
    assert any('复习分组统计' in m.value for m in at.markdown)
    at.session_state['_history_day']=date(2026,10,23);at.run()
    at.button(key='history_note_'+docid).click().run()
    assert not at.exception and any('SQL GROUP BY' in text.value for text in at.text)


def test_search_finds_older_activity_without_model_calls(monkeypatch,tmp_path):
    from rolepath import llm
    at,pid,docid=app(monkeypatch,tmp_path)
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:pytest.fail('History must not call AI'))
    at.session_state['_history_month']=date(2026,11,1);at.session_state['_history_day']=date(2026,11,1)
    at.run();at.text_input(key='ui_dcf5e18a1645').set_value('SQL笔记').run()
    assert not at.exception and at.session_state['_history_day']==date(2026,10,23)
    assert at.session_state['_history_month']==date(2026,10,1)
    assert len([b for b in at.button if b.key and b.key.startswith('history_')])==1


def test_cloud_checkins_are_paginated_and_filtered_by_account():
    from rolepath.cloud_store import CloudStore
    calls=[]
    rows=[dict(task_id='task',day=(date(2026,10,26)-timedelta(days=i)).isoformat(),minutes=10,reflection='practice') for i in range(501)]
    class Query:
        def select(self,*args):return self
        def eq(self,key,value):calls.append(('eq',key,value));return self
        def order(self,key,**kw):calls.append(('order',key));return self
        def range(self,start,end):self.start=start;self.end=end;return self
        def execute(self):return SimpleNamespace(data=rows[self.start:self.end+1])
    store=CloudStore(SimpleNamespace(table=lambda name:Query()),'current-user')
    store.rows=lambda name:[dict(id='task',title='SQL',plan_id='plan')]
    result=store.history_logs()
    assert len(result)==501 and result[-1]['plan_id']=='plan'
    assert calls.count(('eq','user_id','current-user'))==2
    assert ('order','id') not in calls
