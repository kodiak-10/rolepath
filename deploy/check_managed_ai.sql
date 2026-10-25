-- Disposable fixtures and assertions. ROLLBACK removes every test row.
begin;
create temporary table rp_ai_check_results(name text, passed boolean);
do $$
declare a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); rid uuid:=gen_random_uuid();
 r jsonb; balance integer; blocked boolean:=false;
begin
 insert into auth.users(id,aud,role,email,email_confirmed_at) values
 (a,'authenticated','authenticated',a::text||'@example.invalid',now()),
 (b,'authenticated','authenticated',b::text||'@example.invalid',now());
 r:=public.rp_ai_reserve(a,rid,'jd',10000);
 if not (r->>'execute')::boolean then raise exception 'new task not reserved'; end if;
 select remaining into balance from public.rp_ai_wallets where user_id=a;
 if balance<>0 then raise exception 'reservation did not consume credit'; end if;
 insert into rp_ai_check_results values('first reservation',true);
 r:=public.rp_ai_reserve(a,rid,'jd',10000);
 if (r->>'execute')::boolean then raise exception 'duplicate executed'; end if;
 insert into rp_ai_check_results values('duplicate reservation',true);
 begin
  perform public.rp_ai_reserve(a,gen_random_uuid(),'notes',10000);
 exception when others then
  if sqlerrm='TASK_PENDING' then blocked:=true; else raise; end if;
 end;
 if not blocked then raise exception 'parallel task accepted'; end if;
 insert into rp_ai_check_results values('pending task blocked',true);
 perform public.rp_ai_finish(a,rid,false,'[]'::jsonb,null);
 perform public.rp_ai_finish(a,rid,false,'[]'::jsonb,null);
 select remaining into balance from public.rp_ai_wallets where user_id=a;
 if balance<>1 then raise exception 'refund not idempotent'; end if;
 insert into rp_ai_check_results values('single refund',true);
 rid:=gen_random_uuid();
 perform public.rp_ai_reserve(a,rid,'jd',10000);
 perform public.rp_ai_finish(a,rid,true,'[{"total_tokens":3}]'::jsonb,'{"answer":"test"}'::jsonb);
 perform public.rp_ai_finish(a,rid,false,'[]'::jsonb,null);
 select remaining into balance from public.rp_ai_wallets where user_id=a;
 if balance<>0 then raise exception 'successful run refunded'; end if;
 insert into rp_ai_check_results values('success cannot be refunded by replay',true);
 r:=public.rp_ai_reserve(a,rid,'jd',10000);
 if r->>'status'<>'succeeded' or r->'result'->>'answer'<>'test' then raise exception 'result not recoverable'; end if;
 insert into rp_ai_check_results values('saved result recovery',true);
 blocked:=false;
 begin
  perform public.rp_ai_reserve(a,gen_random_uuid(),'jd',10000);
 exception when others then
  if sqlerrm='NO_CREDITS' then blocked:=true; else raise; end if;
 end;
 if not blocked then raise exception 'empty wallet accepted'; end if;
 insert into rp_ai_check_results values('empty balance blocked',true);
 rid:=gen_random_uuid();
 perform public.rp_ai_reserve(b,rid,'notes',10000);
 perform public.rp_ai_finish(b,rid,false,'[]'::jsonb,null);
 select remaining into balance from public.rp_ai_wallets where user_id=b;
 if balance<>1 then raise exception 'second identity free credit missing'; end if;
 insert into rp_ai_check_results values('independent account credit',true);
 perform set_config('request.jwt.claims',json_build_object('sub',b,'role','authenticated')::text,true);
 execute 'set local role authenticated';
 select count(*) into balance from public.rp_ai_wallets where user_id=a;
 if balance<>0 then raise exception 'cross-user wallet visible'; end if;
 select count(*) into balance from public.rp_ai_runs where user_id=a;
 if balance<>0 then raise exception 'cross-user result visible'; end if;
 blocked:=false;
 begin
  update public.rp_ai_wallets set remaining=100;
 exception when insufficient_privilege then blocked:=true;
 end;
 if not blocked then raise exception 'client can alter wallet'; end if;
 blocked:=false;
 begin
  perform public.rp_ai_reserve(b,gen_random_uuid(),'jd',10000);
 exception when insufficient_privilege then blocked:=true;
 end;
 if not blocked then raise exception 'client can invoke accounting'; end if;
 execute 'reset role';
 insert into rp_ai_check_results values('cross-user RLS and client write protection',true);
end $$;
select count(*) filter(where passed) as passed, count(*) filter(where not passed) as failed from rp_ai_check_results;
rollback;
