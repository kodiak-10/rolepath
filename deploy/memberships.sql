-- Monthly memberships. Apply after account_entitlements.sql.
-- Prices and expiry are server controlled; personal QR payments are reviewed manually.
begin;
alter table public.rp_ai_wallets add column if not exists member_until timestamptz;
create table if not exists public.rp_membership_admins (
 user_id uuid primary key references auth.users(id) on delete cascade
);
create table if not exists public.rp_membership_orders (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 code text not null unique,
 product text not null default 'monthly_1290_unlimited_v1' check(product='monthly_1290_unlimited_v1'),
 amount_fen integer not null default 1290 check(amount_fen=1290),
 status text not null default 'awaiting_payment' check(status in('awaiting_payment','submitted','needs_info','approved')),
 created_at timestamptz not null default now(), submitted_at timestamptz,
 paid_at timestamptz, payment_reference text,
 reviewed_at timestamptz, reviewed_by uuid references auth.users(id), review_note text,
 period_start timestamptz, period_end timestamptz
);
create unique index if not exists rp_membership_one_open on public.rp_membership_orders(user_id)
 where status in('awaiting_payment','submitted','needs_info');
alter table public.rp_membership_orders enable row level security;
alter table public.rp_membership_orders force row level security;
alter table public.rp_membership_admins enable row level security;
alter table public.rp_membership_admins force row level security;
revoke all on public.rp_membership_orders,public.rp_membership_admins from public,anon,authenticated;
grant select on public.rp_membership_orders to authenticated;
grant all on public.rp_membership_orders,public.rp_membership_admins to service_role;
drop policy if exists membership_order_owner on public.rp_membership_orders;
create policy membership_order_owner on public.rp_membership_orders for select to authenticated using(auth.uid()=user_id);

create or replace function public.rp_membership_is_admin()
returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.rp_membership_admins where user_id=auth.uid());
$$;

create or replace function public.rp_membership_create_order()
returns jsonb language plpgsql security definer set search_path='' as $$
declare u uuid:=auth.uid(); o public.rp_membership_orders; new_id uuid:=gen_random_uuid();
begin
 if not exists(select 1 from auth.users where id=u and email_confirmed_at is not null) then raise exception 'VERIFIED_ACCOUNT_REQUIRED'; end if;
 insert into public.rp_ai_wallets(user_id) values(u) on conflict do nothing;
 perform 1 from public.rp_ai_wallets where user_id=u for update;
 if exists(select 1 from public.rp_ai_wallets where user_id=u and unlimited) then raise exception 'PERMANENT_ACCESS'; end if;
 select * into o from public.rp_membership_orders where user_id=u and status in('awaiting_payment','submitted','needs_info') for update;
 if found then return to_jsonb(o); end if;
 insert into public.rp_membership_orders(id,user_id,code) values(new_id,u,'RP-'||upper(substr(replace(new_id::text,'-',''),1,12))) returning * into o;
 return to_jsonb(o);
end $$;

create or replace function public.rp_membership_submit_order(p_id uuid,p_paid_at timestamptz,p_reference text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare o public.rp_membership_orders;
begin
 select * into o from public.rp_membership_orders where id=p_id and user_id=auth.uid() for update;
 if not found then raise exception 'ORDER_NOT_FOUND'; end if;
 if o.status in('submitted','approved') then return to_jsonb(o); end if;
 if p_paid_at is null or p_paid_at>now()+interval '5 minutes' or p_paid_at<o.created_at-interval '5 minutes' then raise exception 'INVALID_PAYMENT_TIME'; end if;
 if p_reference is null or length(trim(p_reference))<4 or length(trim(p_reference))>80 then raise exception 'INVALID_PAYMENT_REFERENCE'; end if;
 update public.rp_membership_orders set paid_at=p_paid_at,payment_reference=trim(p_reference),submitted_at=now(),status='submitted' where id=p_id returning * into o;
 return to_jsonb(o);
end $$;

create or replace function public.rp_membership_admin_orders(p_admin uuid,p_query text default '')
returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from public.rp_membership_admins where user_id=p_admin) then raise exception 'ADMIN_REQUIRED'; end if;
 return coalesce((select jsonb_agg(to_jsonb(x)) from (
  select o.*,u.email from public.rp_membership_orders o join auth.users u on u.id=o.user_id
  where (p_query<>'' and (o.code ilike '%'||p_query||'%' or u.email ilike '%'||p_query||'%'))
     or (p_query='' and o.status in('submitted','needs_info'))
  order by o.submitted_at desc nulls last,o.created_at desc limit 100
 ) x),'[]'::jsonb);
end $$;

create or replace function public.rp_membership_review_order(p_admin uuid,p_id uuid,p_approve boolean,p_received_fen integer,p_note text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare o public.rp_membership_orders; w public.rp_ai_wallets; u uuid; starts timestamptz; ends timestamptz;
begin
 if not exists(select 1 from public.rp_membership_admins where user_id=p_admin) then raise exception 'ADMIN_REQUIRED'; end if;
 select user_id into u from public.rp_membership_orders where id=p_id;
 if not found then raise exception 'ORDER_NOT_FOUND'; end if;
 -- Consistent wallet -> order lock order also protects concurrent renewal approvals.
 select * into w from public.rp_ai_wallets where user_id=u for update;
 if not found then raise exception 'WALLET_NOT_FOUND'; end if;
 select * into o from public.rp_membership_orders where id=p_id for update;
 if p_approve is null then raise exception 'INVALID_REVIEW'; end if;
 if p_approve and p_received_fen is distinct from o.amount_fen then raise exception 'PAYMENT_AMOUNT_MISMATCH'; end if;
 if o.status='approved' then return to_jsonb(o); end if;
 if o.status<>'submitted' then raise exception 'ORDER_NOT_SUBMITTED'; end if;
 if p_note is null or length(p_note)>300 then raise exception 'INVALID_REVIEW_NOTE'; end if;
 if not p_approve then
  if length(trim(p_note))<3 then raise exception 'REVIEW_NOTE_REQUIRED'; end if;
  update public.rp_membership_orders set status='needs_info',review_note=trim(p_note),reviewed_by=p_admin,reviewed_at=now() where id=p_id returning * into o;
  return to_jsonb(o);
 end if;
 starts:=greatest(now(),w.member_until);
 ends:=((starts at time zone 'Asia/Shanghai')+interval '1 month') at time zone 'Asia/Shanghai';
 update public.rp_ai_wallets set member_until=ends where user_id=u;
 update public.rp_membership_orders set status='approved',reviewed_at=now(),reviewed_by=p_admin,review_note=trim(p_note),period_start=starts,period_end=ends where id=p_id returning * into o;
 return to_jsonb(o);
end $$;

revoke all on function public.rp_membership_is_admin(),public.rp_membership_create_order(),public.rp_membership_submit_order(uuid,timestamptz,text) from public,anon;
grant execute on function public.rp_membership_is_admin(),public.rp_membership_create_order(),public.rp_membership_submit_order(uuid,timestamptz,text) to authenticated;
revoke all on function public.rp_membership_admin_orders(uuid,text),public.rp_membership_review_order(uuid,uuid,boolean,integer,text) from public,anon,authenticated;
grant execute on function public.rp_membership_admin_orders(uuid,text),public.rp_membership_review_order(uuid,uuid,boolean,integer,text) to service_role;

create or replace function public.rp_ai_reserve(p_user uuid,p_id uuid,p_task text,p_daily_limit integer)
returns jsonb language plpgsql security definer set search_path='' as $$
declare w public.rp_ai_wallets; r public.rp_ai_runs; attempts_today integer; active_access boolean;
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
 active_access:=w.unlimited or coalesce(w.member_until>now(),false);
 if not active_access and w.remaining < 1 then raise exception 'NO_CREDITS'; end if;
 -- Limits paid provider requests, including failed attempts, across all users.
 if not active_access and (select count(*) from public.rp_ai_runs where user_id=p_user and created_at>now()-interval '1 hour') >= 5 then
  raise exception 'RATE_LIMIT';
 end if;
 insert into public.rp_ai_daily(day) values((now() at time zone 'Asia/Shanghai')::date) on conflict do nothing;
 select attempts into attempts_today from public.rp_ai_daily where day=(now() at time zone 'Asia/Shanghai')::date for update;
 if not active_access and attempts_today>=p_daily_limit then raise exception 'DAILY_LIMIT'; end if;
 if not active_access then
 update public.rp_ai_daily set attempts=attempts+1 where day=(now() at time zone 'Asia/Shanghai')::date;
 update public.rp_ai_wallets set remaining=remaining-1 where user_id=p_user;
 end if;
 insert into public.rp_ai_runs(id,user_id,task,charged) values(p_id,p_user,p_task,not active_access) returning * into r;
 return to_jsonb(r) || '{"execute":true}'::jsonb;
end $$;


notify pgrst, 'reload schema';
commit;
