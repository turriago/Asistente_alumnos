-- Galería en la nube para el celular.
-- Fotos y vídeos van a Storage, no a columnas bytea.
-- SQL Editor de Supabase → Run.

create table if not exists public.students (
  student_id text primary key,
  full_name text not null,
  program text not null default '',
  group_name text not null default '',
  updated_at timestamptz not null default now()
);

create table if not exists public.student_media (
  id uuid primary key default gen_random_uuid(),
  student_id text not null references public.students (student_id) on delete cascade,
  kind text not null check (kind in ('photo', 'video', 'card')),
  bucket_path text not null,
  public_url text not null,
  mime text not null,
  byte_size int,
  is_card boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists student_media_student_id_idx on public.student_media (student_id);

alter table public.students enable row level security;
alter table public.student_media enable row level security;

drop policy if exists students_anon_read on public.students;
create policy students_anon_read on public.students
  for select using (true);

drop policy if exists student_media_anon_read on public.student_media;
create policy student_media_anon_read on public.student_media
  for select using (true);

grant select on public.students to anon, authenticated, public;
grant select on public.student_media to anon, authenticated, public;

insert into storage.buckets (id, name, public)
values ('student-media', 'student-media', true)
on conflict (id) do update set public = true;

drop policy if exists student_media_anon_select on storage.objects;
create policy student_media_anon_select on storage.objects
  for select
  using (bucket_id = 'student-media');

create table if not exists public.attendance (
  id uuid primary key default gen_random_uuid(),
  class_code text not null default 'aula1',
  student_id text not null references public.students (student_id) on delete cascade,
  full_name text not null default '',
  source text not null default 'web',
  passed_at timestamptz not null default now(),
  unique (class_code, student_id)
);

create index if not exists attendance_class_idx on public.attendance (class_code);

alter table public.attendance enable row level security;

drop policy if exists attendance_read on public.attendance;
create policy attendance_read on public.attendance
  for select using (true);

drop policy if exists attendance_insert on public.attendance;
create policy attendance_insert on public.attendance
  for insert with check (true);

grant select, insert on public.attendance to anon, authenticated, public;

create table if not exists public.class_sessions (
  id uuid primary key default gen_random_uuid(),
  class_code text not null default 'aula1',
  session_date date not null,
  started_at timestamptz not null default now(),
  unique (class_code, session_date)
);

create index if not exists class_sessions_code_idx
  on public.class_sessions (class_code, session_date desc);

alter table public.class_sessions enable row level security;

drop policy if exists class_sessions_read on public.class_sessions;
create policy class_sessions_read on public.class_sessions
  for select using (true);

drop policy if exists class_sessions_insert on public.class_sessions;
create policy class_sessions_insert on public.class_sessions
  for insert with check (true);

grant select, insert on public.class_sessions to anon, authenticated, public;

alter table public.attendance
  add column if not exists session_id uuid references public.class_sessions (id) on delete cascade;

alter table public.attendance
  add column if not exists session_date date;

insert into public.class_sessions (class_code, session_date, started_at)
select
  a.class_code,
  (timezone('America/Bogota', a.passed_at))::date,
  min(a.passed_at)
from public.attendance a
where a.session_id is null
group by a.class_code, (timezone('America/Bogota', a.passed_at))::date
on conflict (class_code, session_date) do nothing;

update public.attendance a
set
  session_id = s.id,
  session_date = s.session_date
from public.class_sessions s
where a.session_id is null
  and a.class_code = s.class_code
  and (timezone('America/Bogota', a.passed_at))::date = s.session_date;

alter table public.attendance drop constraint if exists attendance_class_code_student_id_key;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'attendance_session_student_uniq'
  ) then
    alter table public.attendance
      add constraint attendance_session_student_uniq unique (session_id, student_id);
  end if;
end $$;

create index if not exists attendance_session_idx on public.attendance (session_id);
