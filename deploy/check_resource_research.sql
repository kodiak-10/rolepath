begin;
do $$
declare u uuid:=gen_random_uuid();v uuid:=gen_random_uuid();r uuid:=gen_random_uuid();r2 uuid:=gen_random_uuid();response jsonb;n integer;checks integer:=0;
begin
 insert into auth.users(id,email,email_confirmed_at) values(u,'web-research-'||u||'@example.invalid',now()),(v,'other-'||v||'@example.invalid',now());
 response:=public.rp_ai_reserve(u,r,'resources',10000);
 if response->>'task'<>'resources' or not (response->>'charged')::boolean then raise exception 'research reservation failed';end if;checks:=checks+1;
 response:=public.rp_ai_finish(u,r,true,'[]','{"topic":"synthetic role","items":[]}');
 if response->>'status'<>'succeeded' or response->'result'->>'topic'<>'synthetic role' then raise exception 'research result not preserved';end if;checks:=checks+1;
 response:=public.rp_ai_reserve(u,r,'resources',10000);
 if (response->>'execute')::boolean then raise exception 'replayed research executes again';end if;checks:=checks+1;
 begin perform public.rp_ai_reserve(u,r,'jd',10000);raise exception 'mismatched task reused';exception when raise_exception then if sqlerrm<>'REQUEST_MISMATCH' then raise;end if;end;checks:=checks+1;
 update public.rp_ai_wallets set remaining=1 where user_id=u;
 perform public.rp_ai_reserve(u,r2,'resources',10000);perform public.rp_ai_finish(u,r2,false,'[]',null);
 if (select remaining from public.rp_ai_wallets where user_id=u)<>1 then raise exception 'research failure not refunded';end if;checks:=checks+1;
 perform set_config('request.jwt.claims',json_build_object('sub',u,'role','authenticated')::text,true);
 execute 'set local role authenticated';
 select count(*) into n from public.rp_ai_runs where task='resources';if n<>2 then raise exception 'own research RLS failed';end if;checks:=checks+1;
 execute 'reset role';
 perform set_config('request.jwt.claims',json_build_object('sub',v,'role','authenticated')::text,true);
 execute 'set local role authenticated';
 select count(*) into n from public.rp_ai_runs where task='resources';if n<>0 then raise exception 'cross user research visible';end if;checks:=checks+1;
 execute 'reset role';
 if has_table_privilege('authenticated','public.rp_ai_runs','update') then raise exception 'client may fake research result';end if;checks:=checks+1;
 if checks<>8 then raise exception 'incomplete checks';end if;
end $$;
select '8 passed, 0 failed; synthetic changes rolled back' as result;
rollback;
