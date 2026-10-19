"""Supabase data access using the current user's JWT and database RLS."""
import json
import uuid


class CloudStore:
    cloud = True

    def __init__(self, client, user_id):
        self.client, self.user_id = client, user_id

    def close(self):
        pass

    def table(self, name):
        return self.client.table('rp_' + name)

    def rows(self, name, **filters):
        result = []
        for start in range(0, 100000, 500):
            query = self.table(name).select('*').eq('user_id', self.user_id).order('id')
            for key, value in filters.items():
                query = query.eq(key, value)
            batch = query.range(start, start + 499).execute().data
            result.extend(batch)
            if len(batch) < 500:
                return result
        raise ValueError('资料数量超过本次读取限制；没有截断结果。')

    def save_plan(self, target, tasks, meta):
        return self.client.rpc('rp_save_plan', {'p_target':target, 'p_tasks':tasks, 'p_meta':meta}).execute().data

    def recent_plan(self):
        data=self.table('plans').select('*').eq('user_id',self.user_id).order('created_at',desc=True).order('id').limit(1).execute().data
        if not data: return None
        row=data[0]
        return {**row,'meta':json.dumps(row['meta'],ensure_ascii=False)}

    def tasks_for(self, plan_id):
        rows=self.rows('tasks',plan_id=plan_id)
        return [{**r['payload'],'status':r['status']} for r in sorted(rows,key=lambda r:r['position'])]

    def set_task_status(self, task_id, status):
        self.table('tasks').update({'status':status}).eq('user_id',self.user_id).eq('id',task_id).execute()

    def log_study(self, task_id, day, minutes, reflection):
        self.table('learning_logs').upsert(dict(user_id=self.user_id,task_id=task_id,day=day,minutes=minutes,reflection=reflection),on_conflict='user_id,task_id,day').execute()

    def study_logs(self, plan_id):
        tasks=self.rows('tasks',plan_id=plan_id)
        result=[]
        for task in tasks:
            start=0
            while True:
                batch=self.table('learning_logs').select('*').eq('user_id',self.user_id).eq('task_id',task['id']).order('day',desc=True).range(start,start+499).execute().data
                result.extend({**r,'title':task['title']} for r in batch)
                if len(batch)<500: break
                start+=500
        return sorted(result,key=lambda r:r['day'],reverse=True)

    def save_document(self, filename, checksum, chunks):
        result=self.client.rpc('rp_save_document',dict(p_filename=filename,p_checksum=checksum,p_chunks=chunks)).execute().data
        return result['id'], result['count']

    def get_documents(self):
        return sorted(self.rows('documents'),key=lambda r:(r['created_at'],r['id']),reverse=True)

    def get_chunks(self):
        return sorted(self.rows('chunks'),key=lambda r:(r['created_at'],r['document_id'],r['page'],r['chunk_no']))

    def delete_document(self, docid):
        self.client.rpc('rp_delete_document',{'p_id':docid}).execute()

    def save_report(self, report):
        rid=str(uuid.uuid4())
        self.table('note_reports').insert(dict(user_id=self.user_id,id=rid,payload=report)).execute()
        return rid

    def reports(self):
        current={r['id'] for r in self.get_chunks()}
        return [(r['id'],r['payload']) for r in sorted(self.rows('note_reports'),key=lambda r:r['created_at'],reverse=True)
                if {s['id'] for s in r['payload']['sources']} <= current]
