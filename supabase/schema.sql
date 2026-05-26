-- Supabase SQL Editor에서 실행

-- uuid 확장
create extension if not exists "uuid-ossp";

-- 구독자 테이블
create table if not exists subscribers (
  id      uuid default uuid_generate_v4() primary key,
  email   text unique not null,
  token   text unique default uuid_generate_v4()::text,
  active  boolean default true,
  created_at timestamptz default now()
);

-- 논문 다이제스트 테이블
create table if not exists digests (
  id      uuid default uuid_generate_v4() primary key,
  date    date unique not null,
  papers  jsonb not null default '[]',
  created_at timestamptz default now()
);

-- RLS 활성화
alter table subscribers enable row level security;
alter table digests enable row level security;

-- 논문은 누구나 읽을 수 있음 (웹 표시용)
create policy "Anyone can read digests"
  on digests for select using (true);

-- 구독자 테이블은 service role만 쓰기 가능 (기본값)

-- 논문 분야 태그 — digests를 외부 스크립트가 덮어써도 살아남도록 분리
create table if not exists paper_tags (
  arxiv_id  text primary key,
  tags      jsonb not null default '[]',
  tagged_at timestamptz default now()
);
alter table paper_tags enable row level security;
create policy "Anyone can read paper_tags"
  on paper_tags for select using (true);
