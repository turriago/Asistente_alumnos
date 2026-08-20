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
