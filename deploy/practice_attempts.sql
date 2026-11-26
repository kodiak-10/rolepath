begin;

create table public.rp_practice_attempts (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    practice_id text not null,
    created_at timestamptz not null default now(),
    submission jsonb not null check (jsonb_typeof(submission) = 'object'),
    feedback jsonb not null check (jsonb_typeof(feedback) = 'object')
);

create index rp_practice_attempts_latest
    on public.rp_practice_attempts (user_id, practice_id, created_at desc, id desc);

alter table public.rp_practice_attempts enable row level security;
revoke all on public.rp_practice_attempts from public, anon, authenticated;
grant select, insert on public.rp_practice_attempts to authenticated;

create policy read_own_practice_attempts on public.rp_practice_attempts
    for select to authenticated using ((select auth.uid()) = user_id);

create policy insert_own_practice_attempts on public.rp_practice_attempts
    for insert to authenticated with check ((select auth.uid()) = user_id);

commit;
