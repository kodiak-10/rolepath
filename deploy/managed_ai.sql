-- Additive migration. Run after supabase.sql. No user records are changed.
-- Only the trusted application server may reserve or settle credits.
begin;
create table if not exists public.rp_ai_wallets (
 user_id uuid primary key references auth.users(id) on delete cascade,
 remaining integer not null default 1 check (remaining >= 0),
 created_at timestamptz not null default now()
);
create table if not exists public.rp_ai_runs (
 id uuid primary key, user_id uuid not null references auth.users(id) on delete cascade,
 task text not null check(task in ('jd','notes','document')),
 status text not null default 'pending' check(status in ('pending','succeeded','failed')),
 created_at timestamptz not null default now(), completed_at timestamptz,
 usage jsonb, result jsonb
);
create unique index if not exists rp_ai_one_pending on public.rp_ai_runs(user_id) where status='pending';
create index if not exists rp_ai_runs_recent on public.rp_ai_runs(user_id,created_at desc);
create table if not exists public.rp_ai_daily (
 day date primary key, attempts integer not null default 0
);
alter table public.rp_ai_wallets enable row level security;
alter table public.rp_ai_runs enable row level security;
alter table public.rp_ai_daily enable row level security;
revoke all on public.rp_ai_wallets, public.rp_ai_runs, public.rp_ai_daily from anon, authenticated;
grant select on public.rp_ai_wallets, public.rp_ai_runs to authenticated;
grant all on public.rp_ai_wallets, public.rp_ai_runs, public.rp_ai_daily to service_role;
create policy ai_wallet_owner on public.rp_ai_wallets for select to authenticated using(auth.uid()=user_id);
create policy ai_run_owner on public.rp_ai_runs for select to authenticated using(auth.uid()=user_id);

create or replace function public.rp_ai_reserve(p_user uuid,p_id uuid,p_task text,p_daily_limit integer)
returns jsonb language plpgsql security definer set search_path='' as $$
declare w public.rp_ai_wallets; r public.rp_ai_runs; attempts_today integer;
begin
 if p_daily_limit < 1 or p_daily_limit > 10000 then raise exception 'INVALID_LIMIT'; end if;
 -- The same verified identity receives the free credit once, even after concurrent requests.
 if not exists(select 1 from auth.users where id=p_user and email_confirmed_at is not null) then
  raise exception 'VERIFIED_ACCOUNT_REQUIRED';
 end if;
 insert into public.rp_ai_wallets(user_id) values(p_user) on conflict do nothing;
 select * into w from public.rp_ai_wallets where user_id=p_user for update;
 select * into r from public.rp_ai_runs where id=p_id;
 if found then
  if r.user_id<>p_user or r.task<>p_task then raise exception 'REQUEST_MISMATCH'; end if;
  return to_jsonb(r) || '{"execute":false}'::jsonb;
 end if;
 if exists(select 1 from public.rp_ai_runs where user_id=p_user and status='pending') then raise exception 'TASK_PENDING'; end if;
 if w.remaining < 1 then raise exception 'NO_CREDITS'; end if;
 -- Limits paid provider requests, including failed attempts, across all users.
 if (select count(*) from public.rp_ai_runs where user_id=p_user and created_at>now()-interval '1 hour') >= 5 then
  raise exception 'RATE_LIMIT';
 end if;
 insert into public.rp_ai_daily(day) values((now() at time zone 'Asia/Shanghai')::date) on conflict do nothing;
 select attempts into attempts_today from public.rp_ai_daily where day=(now() at time zone 'Asia/Shanghai')::date for update;
 if attempts_today>=p_daily_limit then raise exception 'DAILY_LIMIT'; end if;
 update public.rp_ai_daily set attempts=attempts+1 where day=(now() at time zone 'Asia/Shanghai')::date;
 update public.rp_ai_wallets set remaining=remaining-1 where user_id=p_user;
 insert into public.rp_ai_runs(id,user_id,task) values(p_id,p_user,p_task) returning * into r;
 return to_jsonb(r) || '{"execute":true}'::jsonb;
end $$;

create or replace function public.rp_ai_finish(p_user uuid,p_id uuid,p_success boolean,p_usage jsonb,p_result jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.rp_ai_runs;
begin
 -- Use the same lock order as reserve.
 perform 1 from public.rp_ai_wallets where user_id=p_user for update;
 select * into r from public.rp_ai_runs where id=p_id and user_id=p_user for update;
 if not found then raise exception 'REQUEST_NOT_FOUND'; end if;
 if r.status<>'pending' then return to_jsonb(r); end if;
 if p_success and (p_result is null or p_result='null'::jsonb) then raise exception 'RESULT_REQUIRED'; end if;
 update public.rp_ai_runs set status=case when p_success then 'succeeded' else 'failed' end,
  completed_at=now(),usage=p_usage,result=case when p_success then p_result else null end
  where id=p_id returning * into r;
 if not p_success then update public.rp_ai_wallets set remaining=remaining+1 where user_id=p_user; end if;
 return to_jsonb(r);
end $$;
revoke all on function public.rp_ai_reserve(uuid,uuid,text,integer) from public,anon,authenticated;
revoke all on function public.rp_ai_finish(uuid,uuid,boolean,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.rp_ai_reserve(uuid,uuid,text,integer) to service_role;
grant execute on function public.rp_ai_finish(uuid,uuid,boolean,jsonb,jsonb) to service_role;
commit;
