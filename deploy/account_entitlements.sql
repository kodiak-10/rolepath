-- Apply after managed_ai.sql. Entitlements remain server controlled.
begin;
alter table public.rp_ai_wallets add column if not exists unlimited boolean not null default false;
-- Existing pending tasks reserved a credit under the previous ledger.
alter table public.rp_ai_runs add column if not exists charged boolean not null default true;
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
 if not w.unlimited and w.remaining < 1 then raise exception 'NO_CREDITS'; end if;
 -- Limits paid provider requests, including failed attempts, across all users.
 if not w.unlimited and (select count(*) from public.rp_ai_runs where user_id=p_user and created_at>now()-interval '1 hour') >= 5 then
  raise exception 'RATE_LIMIT';
 end if;
 insert into public.rp_ai_daily(day) values((now() at time zone 'Asia/Shanghai')::date) on conflict do nothing;
 select attempts into attempts_today from public.rp_ai_daily where day=(now() at time zone 'Asia/Shanghai')::date for update;
 if not w.unlimited and attempts_today>=p_daily_limit then raise exception 'DAILY_LIMIT'; end if;
 if not w.unlimited then
 update public.rp_ai_daily set attempts=attempts+1 where day=(now() at time zone 'Asia/Shanghai')::date;
 update public.rp_ai_wallets set remaining=remaining-1 where user_id=p_user;
 end if;
 insert into public.rp_ai_runs(id,user_id,task,charged) values(p_id,p_user,p_task,not w.unlimited) returning * into r;
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
 if not p_success and r.charged then update public.rp_ai_wallets set remaining=remaining+1 where user_id=p_user; end if;
 return to_jsonb(r);
end $$;
revoke all on function public.rp_ai_reserve(uuid,uuid,text,integer) from public,anon,authenticated;
revoke all on function public.rp_ai_finish(uuid,uuid,boolean,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.rp_ai_reserve(uuid,uuid,text,integer) to service_role;
grant execute on function public.rp_ai_finish(uuid,uuid,boolean,jsonb,jsonb) to service_role;
commit;
