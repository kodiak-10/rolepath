-- RolePath: dedicated schema objects. Run once in a new Supabase project.
-- API clients use the public key and the signed-in user's JWT, never service_role.
begin;
create table public.rp_plans (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id uuid not null, created_at timestamptz not null default now(),
  target text not null, meta jsonb not null,
  primary key(user_id,id)
);
create table public.rp_tasks (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id text not null, plan_id uuid not null, position integer not null,
  title text not null, payload jsonb not null,
  status text not null default '待完成' check(status in ('待完成','已完成')),
  primary key(user_id,id),
  foreign key(user_id,plan_id) references public.rp_plans(user_id,id) on delete cascade
);
create table public.rp_learning_logs (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  task_id text not null, day date not null,
  minutes integer not null check(minutes between 1 and 1440), reflection text not null,
  primary key(user_id,task_id,day),
  foreign key(user_id,task_id) references public.rp_tasks(user_id,id) on delete cascade
);
create table public.rp_documents (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id uuid not null, filename text not null, checksum text not null,
  created_at timestamptz not null default now(),
  primary key(user_id,id), unique(user_id,checksum)
);
create table public.rp_chunks (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id text not null, document_id uuid not null, filename text not null,
  page integer not null, chunk_no integer not null, content text not null,
  created_at timestamptz not null default now(),
  primary key(user_id,id),
  foreign key(user_id,document_id) references public.rp_documents(user_id,id) on delete cascade
);
create table public.rp_note_reports (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id uuid not null, payload jsonb not null, created_at timestamptz not null default now(),
  primary key(user_id,id)
);
-- Enforced by the database for every SELECT, INSERT, UPDATE and DELETE.
do $$
declare tab text;
begin
  foreach tab in array array['rp_plans','rp_tasks','rp_learning_logs','rp_documents','rp_chunks','rp_note_reports'] loop
    execute format('alter table public.%I enable row level security',tab);
    execute format('alter table public.%I force row level security',tab);
    execute format('revoke all on public.%I from anon',tab);
    execute format('grant select,insert,update,delete on public.%I to authenticated',tab);
    execute format('create policy own_records on public.%I for all to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id)',tab);
  end loop;
end $$;
create index rp_plans_recent on public.rp_plans(user_id,created_at desc);
create index rp_chunks_document on public.rp_chunks(user_id,document_id);
create index rp_reports_recent on public.rp_note_reports(user_id,created_at desc);
-- Invoker functions preserve RLS and atomically write parent and child rows.
create function public.rp_save_plan(p_target text, p_tasks jsonb, p_meta jsonb)
returns uuid language plpgsql security invoker set search_path = '' as $$
declare pid uuid := gen_random_uuid(); item jsonb; pos integer := 0;
begin
 if auth.uid() is null then raise exception 'Login required'; end if;
 insert into public.rp_plans(id,target,meta) values(pid,p_target,p_meta);
 for item in select value from jsonb_array_elements(p_tasks) loop
  insert into public.rp_tasks(id,plan_id,position,title,payload) values(item->>'id',pid,pos,item->>'title',item);
  pos:=pos+1;
 end loop;
 return pid;
end $$;
create function public.rp_save_document(p_filename text,p_checksum text,p_chunks jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare did uuid; item jsonb; n integer := 0;
begin
 if auth.uid() is null then raise exception 'Login required'; end if;
 insert into public.rp_documents(id,filename,checksum) values(gen_random_uuid(),p_filename,p_checksum)
 on conflict(user_id,checksum) do nothing returning id into did;
 if did is null then
  select id into did from public.rp_documents where user_id=auth.uid() and checksum=p_checksum;
  return jsonb_build_object('id',did,'count',0);
 end if;
 for item in select value from jsonb_array_elements(p_chunks) loop
  insert into public.rp_chunks(id,document_id,filename,page,chunk_no,content)
  values(did::text||':'||(item->>'page')||':'||(item->>'chunk_no'),did,p_filename,(item->>'page')::integer,(item->>'chunk_no')::integer,item->>'content');
  n:=n+1;
 end loop;
 if n=0 then raise exception 'No text chunks'; end if;
 return jsonb_build_object('id',did,'count',n);
end $$;
create function public.rp_delete_document(p_id uuid)
returns void language plpgsql security invoker set search_path = '' as $$
begin
 delete from public.rp_note_reports where user_id=auth.uid() and exists(
  select 1 from jsonb_array_elements(payload->'sources') s where s->>'document_id'=p_id::text);
 delete from public.rp_documents where id=p_id and user_id=auth.uid();
end $$;
revoke all on function public.rp_save_plan(text,jsonb,jsonb),public.rp_save_document(text,text,jsonb),public.rp_delete_document(uuid) from public,anon;
grant execute on function public.rp_save_plan(text,jsonb,jsonb),public.rp_save_document(text,text,jsonb),public.rp_delete_document(uuid) to authenticated;
commit;
