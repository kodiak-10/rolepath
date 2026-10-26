-- Transactional regression checks. All synthetic rows are rolled back.
-- Apply account_entitlements.sql first. No model requests or emails are sent.
begin;
do $$
declare
 owner_id uuid := gen_random_uuid(); visitor_id uuid := gen_random_uuid();
 run_id uuid; response jsonb; balance integer; attempts_before integer; checks integer := 0;
begin
 insert into auth.users(id,email,email_confirmed_at) values
 (owner_id,'ledger-unlimited-'||owner_id||'@example.invalid',now()),
 (visitor_id,'ledger-standard-'||visitor_id||'@example.invalid',now());
 insert into public.rp_ai_wallets(user_id,remaining,unlimited) values(owner_id,0,true);
 select coalesce(sum(attempts),0) into attempts_before from public.rp_ai_daily;
 for i in 1..7 loop
  run_id := gen_random_uuid();
  response := public.rp_ai_reserve(owner_id,run_id,'jd',1);
  if (response->>'charged')::boolean or not (response->>'execute')::boolean then raise exception 'unlimited reservation failed'; end if;
  response := public.rp_ai_finish(owner_id,run_id,true,'[]','{"answer":"synthetic"}');
  if response->>'status'<>'succeeded' then raise exception 'unlimited settlement failed'; end if;
 end loop;
 select remaining into balance from public.rp_ai_wallets where user_id=owner_id;
 if balance<>0 then raise exception 'unlimited balance changed'; end if; checks:=checks+1;
 if (select coalesce(sum(attempts),0) from public.rp_ai_daily)<>attempts_before then raise exception 'unlimited run consumed daily quota'; end if; checks:=checks+1;
 run_id:=gen_random_uuid();
 perform public.rp_ai_reserve(owner_id,run_id,'notes',1);
 perform public.rp_ai_finish(owner_id,run_id,false,'[]',null);
 if (select remaining from public.rp_ai_wallets where user_id=owner_id)<>0 then raise exception 'unlimited failure created credit'; end if; checks:=checks+1;
 -- Ensure the ordinary account still receives exactly one trial credit.
 run_id:=gen_random_uuid();
 response:=public.rp_ai_reserve(visitor_id,run_id,'jd',10000);
 if not (response->>'charged')::boolean then raise exception 'ordinary task not charged'; end if;
 perform public.rp_ai_finish(visitor_id,run_id,true,'[]','{"answer":"synthetic"}');
 if (select remaining from public.rp_ai_wallets where user_id=visitor_id)<>0 then raise exception 'ordinary balance incorrect'; end if; checks:=checks+1;
 begin
  perform public.rp_ai_reserve(visitor_id,gen_random_uuid(),'jd',10000);
  raise exception 'empty balance allowed';
 exception when raise_exception then
  if sqlerrm<>'NO_CREDITS' then raise; end if;
 end; checks:=checks+1;
 -- An entitlement change must not break refunds of a previously charged run.
 update public.rp_ai_wallets set remaining=1 where user_id=visitor_id;
 run_id:=gen_random_uuid();perform public.rp_ai_reserve(visitor_id,run_id,'jd',10000);
 update public.rp_ai_wallets set unlimited=true where user_id=visitor_id;
 perform public.rp_ai_finish(visitor_id,run_id,false,'[]',null);
 if (select remaining from public.rp_ai_wallets where user_id=visitor_id)<>1 then raise exception 'charged refund lost after entitlement change'; end if; checks:=checks+1;
 if has_table_privilege('authenticated','public.rp_ai_wallets','UPDATE') or has_column_privilege('authenticated','public.rp_ai_wallets','unlimited','UPDATE') then raise exception 'visitor can grant entitlement'; end if; checks:=checks+1;
 if has_function_privilege('authenticated','public.rp_ai_reserve(uuid,uuid,text,integer)','EXECUTE') then raise exception 'visitor can reserve outside server'; end if; checks:=checks+1;
 if checks<>8 then raise exception 'incomplete checks'; end if;
end $$;
select '8 passed, 0 failed; synthetic changes rolled back' as result;
rollback;
