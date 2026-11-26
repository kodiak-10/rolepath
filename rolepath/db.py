from __future__ import annotations
import os
import json
import sqlite3
import uuid
from pathlib import Path

DB_FILE = '.rolepath.sqlite3'

def connect(path=None):
    if path is None and os.getenv('ROLEPATH_CLOUD') == '1':
        import streamlit as st
        from .cloud_store import CloudStore
        if not st.session_state.get('_account_id') or not st.session_state.get('_account_client'):
            raise RuntimeError('请先登录；云端不会读取本机数据库。')
        return CloudStore(st.session_state['_account_client'], st.session_state['_account_id'])
    path = path or DB_FILE
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, target TEXT NOT NULL, meta TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE, title TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT '待完成');
    ''')
    return conn

def save_plan(conn, target:str, tasks:list[dict], meta:dict) -> str:
    if getattr(conn,'cloud',False): return conn.save_plan(target,tasks,meta)
    plan_id=str(uuid.uuid4())
    with conn:
        conn.execute('INSERT INTO plans(id,target,meta) VALUES(?,?,?)',(plan_id,target,json.dumps(meta,ensure_ascii=False)))
        conn.executemany('INSERT INTO tasks(id,plan_id,title,payload,status) VALUES(?,?,?,?,?)', [
            (t['id'],plan_id,t['title'],json.dumps(t,ensure_ascii=False),'待完成') for t in tasks
        ])
    return plan_id

def recent_plan(conn):
    if getattr(conn,'cloud',False): return conn.recent_plan()
    return conn.execute('SELECT * FROM plans ORDER BY created_at DESC, rowid DESC LIMIT 1').fetchone()

def tasks_for(conn, plan_id:str) -> list[dict]:
    if getattr(conn,'cloud',False): return conn.tasks_for(plan_id)
    rows=conn.execute('SELECT * FROM tasks WHERE plan_id=? ORDER BY rowid',(plan_id,)).fetchall()
    return [{**json.loads(x['payload']), 'status':x['status']} for x in rows]

def set_task_status(conn, task_id:str, status:str):
    if status not in ('待完成','已完成'):
        raise ValueError('无效状态')
    if getattr(conn,'cloud',False): return conn.set_task_status(task_id,status)
    with conn:
        conn.execute('UPDATE tasks SET status=? WHERE id=?',(status,task_id))


def ensure_learning_log(conn):
    if getattr(conn,'cloud',False): return
    conn.execute('''CREATE TABLE IF NOT EXISTS learning_logs (
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        day TEXT NOT NULL, minutes INTEGER NOT NULL CHECK(minutes BETWEEN 1 AND 1440),
        reflection TEXT NOT NULL, PRIMARY KEY(task_id,day))''')


def log_study(conn, task_id, minutes, reflection, day=None):
    from datetime import date
    ensure_learning_log(conn)
    day = day or date.today()
    if not isinstance(minutes, int) or not 1 <= minutes <= 1440 or not reflection.strip():
        raise ValueError('请填写有效学习时长和学习记录')
    if day > date.today():
        raise ValueError('不能提前打卡')
    if getattr(conn,'cloud',False): return conn.log_study(task_id,day.isoformat(),minutes,reflection.strip())
    with conn:
        conn.execute('INSERT INTO learning_logs VALUES(?,?,?,?) ON CONFLICT(task_id,day) DO UPDATE SET minutes=excluded.minutes,reflection=excluded.reflection',
            (task_id, day.isoformat(), minutes, reflection.strip()))


def study_stats(conn, plan_id, today=None):
    from datetime import date, timedelta
    today = today or date.today()
    ensure_learning_log(conn)
    rows = conn.study_logs(plan_id) if getattr(conn,'cloud',False) else list(conn.execute('SELECT l.*,t.title FROM learning_logs l JOIN tasks t ON t.id=l.task_id WHERE t.plan_id=? ORDER BY day DESC', (plan_id,)))
    valid = [r for r in rows if date.fromisoformat(r['day']) <= today]
    days = {date.fromisoformat(r['day']) for r in valid}
    cursor = today if today in days else today-timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    week_start = today-timedelta(days=today.weekday())
    return dict(streak=streak, days=len(days), minutes=sum(r['minutes'] for r in valid),
        week_minutes=sum(r['minutes'] for r in valid if date.fromisoformat(r['day']) >= week_start), logs=[dict(r) for r in rows])


def all_plans(conn):
    if getattr(conn, 'cloud', False):
        rows = conn.rows('plans')
        return [{**r, 'meta': json.dumps(r['meta'], ensure_ascii=False)} for r in sorted(rows, key=lambda r:(r['created_at'],r['id']), reverse=True)]
    return list(conn.execute('SELECT * FROM plans ORDER BY created_at DESC, rowid DESC'))


def ensure_practice(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS practice_attempts (
        id TEXT PRIMARY KEY, practice_id TEXT NOT NULL, created_at TEXT NOT NULL,
        submission TEXT NOT NULL, feedback TEXT NOT NULL)''')


def save_practice_attempt(conn, practice_id, submission, feedback):
    if getattr(conn, 'cloud', False):
        return conn.save_practice_attempt(practice_id, submission, feedback)
    from datetime import datetime
    ensure_practice(conn)
    attempt_id = str(uuid.uuid4())
    with conn:
        conn.execute('INSERT INTO practice_attempts(id,practice_id,created_at,submission,feedback) VALUES(?,?,?,?,?)',
            (attempt_id, practice_id, datetime.now().strftime('%Y-%m-%d %H:%M'),
             json.dumps(submission, ensure_ascii=False), json.dumps(feedback, ensure_ascii=False)))
    return attempt_id


def latest_practice_attempt(conn, practice_id):
    if getattr(conn, 'cloud', False):
        return conn.latest_practice_attempt(practice_id)
    ensure_practice(conn)
    row = conn.execute('SELECT * FROM practice_attempts WHERE practice_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1',
        (practice_id,)).fetchone()
    if not row:
        return None
    return dict(id=row['id'], practice_id=row['practice_id'], created_at=row['created_at'],
                submission=json.loads(row['submission']), feedback=json.loads(row['feedback']))


def history_logs(conn):
    """Read actual check-ins across plans for the account calendar."""
    if getattr(conn, 'cloud', False):
        return conn.history_logs()
    ensure_learning_log(conn)
    return [dict(r) for r in conn.execute('''
        SELECT l.*, t.title, t.plan_id FROM learning_logs l
        JOIN tasks t ON t.id=l.task_id ORDER BY l.day DESC, l.task_id
    ''')]
