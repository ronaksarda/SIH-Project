-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- PROFILES
create table if not exists public.profiles (
  id uuid references auth.users not null primary key,
  name text,
  role text check (role in ('inspector', 'officer')) default 'inspector',
  email text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Function to safely check if current user is an officer without causing RLS recursion
create or replace function public.is_officer()
returns boolean as $$
declare
  is_off boolean;
begin
  select exists(
    select 1 from public.profiles
    where id = auth.uid() and role = 'officer'
  ) into is_off;
  return is_off;
end;
$$ language plpgsql security definer set search_path = public;

-- Trigger to automatically create a profile when a new user signs up
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, name, email, role)
  values (new.id, new.raw_user_meta_data->>'full_name', new.email, 'inspector')
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer set search_path = public;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- INSPECTIONS
create table if not exists public.inspections (
  id uuid default uuid_generate_v4() primary key,
  inspector_id uuid references public.profiles(id) not null,
  product_name text not null,
  status text check (status in ('pass', 'fail', 'review')) default 'review',
  location text,
  image_path text,
  inspection_timestamp timestamp with time zone default timezone('utc'::text, now()) not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- DECLARATIONS
create table if not exists public.declarations (
  id uuid default uuid_generate_v4() primary key,
  inspection_id uuid references public.inspections(id) on delete cascade not null,
  mrp text,
  net_quantity text,
  mfg_date text,
  manufacturer_address text,
  consumer_care text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- VIOLATIONS
create table if not exists public.violations (
  id uuid default uuid_generate_v4() primary key,
  inspection_id uuid references public.inspections(id) on delete cascade not null,
  description text not null,
  severity text check (severity in ('low', 'medium', 'high')) default 'medium',
  detected_value text,
  expected_requirement text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- REPORTS
create table if not exists public.reports (
  id uuid default uuid_generate_v4() primary key,
  inspection_id uuid references public.inspections(id) on delete cascade not null,
  pdf_url text,
  docx_url text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- ROW LEVEL SECURITY (RLS)
alter table public.profiles enable row level security;
alter table public.inspections enable row level security;
alter table public.declarations enable row level security;
alter table public.violations enable row level security;
alter table public.reports enable row level security;

-- Drop existing policies for idempotency
drop policy if exists "Users can view their own profile" on profiles;
drop policy if exists "Officers can view all profiles" on profiles;
drop policy if exists "Users can update their own profile" on profiles;

drop policy if exists "Inspectors can create their own inspections" on inspections;
drop policy if exists "Inspectors can view their own inspections" on inspections;
drop policy if exists "Officers can view all inspections" on inspections;

drop policy if exists "Inspectors can create declarations for their inspections" on declarations;
drop policy if exists "Inspectors can view declarations for their inspections" on declarations;
drop policy if exists "Officers can view all declarations" on declarations;

drop policy if exists "Inspectors can create violations for their inspections" on violations;
drop policy if exists "Inspectors can view violations for their inspections" on violations;
drop policy if exists "Officers can view all violations" on violations;

drop policy if exists "Inspectors can view reports for their inspections" on reports;
drop policy if exists "Officers can view all reports" on reports;

-- Policies for Profiles
create policy "Users can view their own profile" on profiles for select using (auth.uid() = id);
create policy "Officers can view all profiles" on profiles for select using (public.is_officer());
create policy "Users can update their own profile" on profiles for update using (auth.uid() = id);

-- Policies for Inspections
create policy "Inspectors can create their own inspections" on inspections for insert with check (auth.uid() = inspector_id);
create policy "Inspectors can view their own inspections" on inspections for select using (auth.uid() = inspector_id);
create policy "Officers can view all inspections" on inspections for select using (public.is_officer());

-- Policies for Declarations
create policy "Inspectors can create declarations for their inspections" on declarations for insert with check (
  exists (select 1 from inspections where id = inspection_id and inspector_id = auth.uid())
);
create policy "Inspectors can view declarations for their inspections" on declarations for select using (
  exists (select 1 from inspections where id = inspection_id and inspector_id = auth.uid())
);
create policy "Officers can view all declarations" on declarations for select using (public.is_officer());

-- Policies for Violations
create policy "Inspectors can create violations for their inspections" on violations for insert with check (
  exists (select 1 from inspections where id = inspection_id and inspector_id = auth.uid())
);
create policy "Inspectors can view violations for their inspections" on violations for select using (
  exists (select 1 from inspections where id = inspection_id and inspector_id = auth.uid())
);
create policy "Officers can view all violations" on violations for select using (public.is_officer());

-- Policies for Reports
create policy "Inspectors can view reports for their inspections" on reports for select using (
  exists (select 1 from inspections where id = inspection_id and inspector_id = auth.uid())
);
create policy "Officers can view all reports" on reports for select using (public.is_officer());

-- STORAGE SETUP (For Inspections Images)
insert into storage.buckets (id, name, public) 
values ('inspections', 'inspections', false)
on conflict (id) do update set public = false;

-- Storage policies
drop policy if exists "Authenticated users can upload images" on storage.objects;
drop policy if exists "Public can view inspection images" on storage.objects;
drop policy if exists "Inspectors can upload their own images" on storage.objects;
drop policy if exists "Inspectors can view their own images" on storage.objects;
drop policy if exists "Officers can view all images" on storage.objects;

-- Ensure inspectors can only upload to a folder matching their own UUID
create policy "Inspectors can upload their own images" on storage.objects for insert with check (
  bucket_id = 'inspections' and 
  auth.role() = 'authenticated' and
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Ensure inspectors can only view images in their own folder
create policy "Inspectors can view their own images" on storage.objects for select using (
  bucket_id = 'inspections' and 
  auth.role() = 'authenticated' and
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Officers can view all images
create policy "Officers can view all images" on storage.objects for select using (
  bucket_id = 'inspections' and 
  auth.role() = 'authenticated' and
  public.is_officer()
);
