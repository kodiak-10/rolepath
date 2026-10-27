-- Record live resource research under the same user-owned, server-reserved ledger.
begin;
alter table public.rp_ai_runs drop constraint rp_ai_runs_task_check;
alter table public.rp_ai_runs add constraint rp_ai_runs_task_check check(task in ('jd','notes','document','resources'));
notify pgrst, 'reload schema';
commit;
