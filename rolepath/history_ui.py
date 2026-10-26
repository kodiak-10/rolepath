"""An account-scoped activity calendar over existing saved learning records."""
import calendar
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo
import streamlit as st
import streamlit.components.v2 as components
from .db import connect, all_plans, history_logs
from .knowledge import get_documents
from .notes import reports
from .i18n import t as tr, language

_ZONE = ZoneInfo('Asia/Shanghai')
_ROOT = Path(__file__).parent
_calendar = components.component('learning_calendar', html='<div class="rp-calendar"></div>',
    css=(_ROOT/'calendar.css').read_text(), js=(_ROOT/'calendar.js').read_text())
def kind_labels():
    return {'plan':tr('学习计划'), 'note':tr('学习笔记'), 'study':tr('学习打卡'), 'analysis':tr('分析与汇总')}


def saved_time(value, naive_zone=timezone.utc):
    moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=naive_zone)
    return moment.astimezone(_ZONE)


def load_events(con):
    events = []
    def add(kind, ident, value, title, payload, search='', naive_zone=timezone.utc):
        moment = saved_time(value, naive_zone)
        events.append(dict(id=kind+'_'+str(ident), kind=kind, day=moment.date(),
                           time=moment.strftime('%H:%M'), order=moment.isoformat(),
                           title=title, payload=payload, search=(title+' '+search).casefold()))
    for row in all_plans(con):
        plan = dict(row)
        add('plan', plan['id'], plan['created_at'], plan['target'], plan)
    for row in get_documents(con):
        doc = dict(row)
        add('note', doc['id'], doc['created_at'], doc['filename'], doc)
    for ident, report in reports(con):
        add('analysis', ident, report['created_at'], report.get('instruction') or tr('笔记总结'), report,
            search=' '.join(s['filename'] for s in report['sources']),
            naive_zone=timezone.utc if getattr(con, 'cloud', False) else _ZONE)
    for row in history_logs(con):
        day = date.fromisoformat(row['day'])
        events.append(dict(id='study_'+row['task_id']+'_'+row['day'], kind='study', day=day,
                           time='', order=day.isoformat(), title=row['title'], payload=row,
                           search=(row['title']+' '+row['reflection']).casefold()))
    return sorted(events, key=lambda event:(event['day'], event['order'], event['id']), reverse=True)


def month_shift(month, offset):
    index = month.year*12 + month.month-1 + offset
    year, index = divmod(index, 12)
    return date(year, index+1, 1)


def calendar_data(month, selected, events, today):
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
    while len(weeks) < 6:
        weeks.append([weeks[-1][-1] + timedelta(days=i) for i in range(1,8)])
    counts = {}
    for event in events:
        counts.setdefault(event['day'], Counter())[event['kind']] += 1
    days = []
    for week in weeks:
        for day in week:
            count = counts.get(day, {})
            days.append(dict(iso=day.isoformat(), number=day.day, inMonth=day.month==month.month,
                selected=day==selected, today=day==today, counts=count,
                label=tr('{0}，{1} 条记录', day.isoformat(), sum(count.values()))))
    weekdays = ['一','二','三','四','五','六','日'] if language()=='zh' else ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    title = f'{month.year} 年 {month.month} 月' if language()=='zh' else f'{calendar.month_name[month.month]} {month.year}'
    return dict(month=month.isoformat(), title=title, days=days, weekdays=weekdays,
        labels=dict(previous=tr('上个月'), next=tr('下个月'), today=tr('今天'), calendar=tr('学习日历')))


def apply_calendar_action(action, month, today):
    if not isinstance(action, dict) or action.get('month') != month.isoformat():
        raise ValueError('日历操作无效，请刷新页面。')
    if action.get('type') == 'day':
        chosen = date.fromisoformat(action['day'])
        if not month-timedelta(days=6) <= chosen <= month_shift(month,1)+timedelta(days=13):
            raise ValueError('日期不在当前日历中。')
        return chosen.replace(day=1), chosen
    if action.get('type') in ('previous','next'):
        next_month = month_shift(month, -1 if action['type']=='previous' else 1)
        return next_month, next_month
    if action.get('type') == 'today':
        return today.replace(day=1), today
    raise ValueError('日历操作无效，请刷新页面。')


def render_event(event):
    from .ui import restore_plan
    kind = event['kind']; row = event['payload']
    with st.container(key='activity_'+event['id'], border=True):
        st.markdown('<span class="rp-event-tag '+kind+'">'+escape(kind_labels()[kind])+'</span>'
                    '<span class="rp-event-time">'+escape(event['time'])+'</span>', unsafe_allow_html=True)
        st.write(event['title'])
        if kind == 'plan':
            st.button(tr('继续这份计划'), key='history_'+row['id'], on_click=restore_plan, args=(row,), use_container_width=True)
        elif kind == 'note':
            if st.button(tr('打开笔记'), key='history_note_'+row['id'], use_container_width=True):
                from .notes_ui import open_document
                open_document(row)
        elif kind == 'study':
            st.caption(tr('学习 {0} 分钟', row['minutes']))
            st.write(row['reflection'])
        else:
            with st.expander(tr('查看分析内容')):
                for item in row['items']:
                    st.write(item['kind']+'：'+item['text'])


def render_history():
    today = datetime.now(_ZONE).date()
    st.subheader(tr('学习日历'))
    st.caption(tr('点选日期，回看当天的计划、笔记和学习记录。'))
    query = st.text_input(tr('搜索历史记录'), placeholder=tr('搜索岗位、笔记或学习内容…'), key='ui_dcf5e18a1645').strip().casefold()
    con = connect()
    try:
        events = [event for event in load_events(con) if query in event['search']]
    finally:
        con.close()
    st.session_state.setdefault('_history_month', today.replace(day=1))
    st.session_state.setdefault('_history_day', today)
    if query != st.session_state.get('_history_query'):
        st.session_state['_history_query'] = query
        if query and events:
            st.session_state['_history_day'] = events[0]['day']
            st.session_state['_history_month'] = events[0]['day'].replace(day=1)
    month = st.session_state['_history_month']; selected = st.session_state['_history_day']
    left, right = st.columns([1.65,1], gap='large')
    with left:
        data = calendar_data(month, selected, events, today)
        result = _calendar(data=data, key='learning_calendar', on_action_change=lambda:None)
        action = result.action
        if action:
            new_month, chosen = apply_calendar_action(action, month, today)
            st.session_state['_history_month'] = new_month
            st.session_state['_history_day'] = chosen
            st.rerun()
        legend = ''.join('<span><i class="'+kind+'"></i>'+escape(label)+'</span>' for kind,label in kind_labels().items())
        st.markdown('<div class="rp-calendar-legend">'+legend+'</div>', unsafe_allow_html=True)
        monthly = [e for e in events if e['day'].year==month.year and e['day'].month==month.month]
        minutes = sum(e['payload']['minutes'] for e in monthly if e['kind']=='study')
        st.caption(tr('本月 {0} 条记录 · 学习 {1} 分钟', len(monthly), minutes))
    with right:
        title = f'{selected.month}月{selected.day}日' if language()=='zh' else selected.strftime('%b %d, %Y')
        st.markdown('### '+title)
        daily = [event for event in events if event['day']==selected]
        st.caption(tr('{0} 条记录',len(daily)))
        if not daily:
            st.markdown('<div class="rp-day-empty"><span>◌</span><p>'+tr('这一天还没有记录。')+'</p></div>', unsafe_allow_html=True)
        for event in daily:
            render_event(event)
