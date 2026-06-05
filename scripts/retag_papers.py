"""
기존 digest 논문들을 재태깅해서 hf_papers / papers 컬럼 인라인 tags를 업데이트한다.
사이드바 누적 카운트가 0으로 표시될 때 실행.

사용법:
  GROQ_API_KEY=... SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/retag_papers.py

옵션:
  --days N   최근 N일치 digest만 처리 (기본: 31, 현재 달 전체 커버)
  --all      전체 history 재태깅
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# daily_digest의 tag_paper / TAG_CATEGORIES 재사용
sys.path.insert(0, str(Path(__file__).parent))
from daily_digest import tag_paper, TAG_CATEGORIES, VALID_TAGS  # noqa: E402

from supabase import create_client


def fetch_digests(sb, since_date: str):
    """since_date 이후 모든 digest 반환 (date 오름차순)"""
    # hf_papers 컬럼 시도
    r = sb.table("digests").select("date, hf_papers, papers").gte("date", since_date).order("date").execute()
    if r.data:
        return r.data
    # 없으면 papers 컬럼만
    r = sb.table("digests").select("date, papers").gte("date", since_date).order("date").execute()
    return r.data or []


def pick_papers(row: dict) -> list:
    hf = row.get("hf_papers")
    if isinstance(hf, list) and hf:
        return hf
    raw = row.get("papers")
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("papers"), list):
        return raw["papers"]
    return []


def retag_digest(sb, row: dict, groq_key: str) -> int:
    papers = pick_papers(row)
    if not papers:
        return 0

    updated = 0
    for p in papers:
        arxiv_id = p.get("arxiv_id", "")
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        current_tags = p.get("tags", [])

        if current_tags:
            print(f"  skip {arxiv_id} (already tagged: {current_tags})")
            continue

        if not abstract:
            print(f"  skip {arxiv_id} (no abstract)")
            continue

        print(f"  tagging {arxiv_id[:20]}  '{title[:50]}'…")
        tags = tag_paper(title, abstract, groq_key)
        print(f"    → {tags}")
        p["tags"] = tags
        updated += 1
        time.sleep(1)

    if updated == 0:
        return 0

    date_str = row["date"]
    col = "hf_papers" if isinstance(row.get("hf_papers"), list) else "papers"

    # papers 컬럼이 {"papers": [...]} 형태인 경우 그대로 유지
    if col == "papers" and isinstance(row.get("papers"), dict):
        payload = {col: {"papers": papers}}
    else:
        payload = {col: papers}

    payload["date"] = date_str
    sb.table("digests").upsert(payload, on_conflict="date").execute()
    print(f"  ✔ {date_str} digest 업데이트 ({updated}건 재태깅)")

    # paper_tags 테이블이 있으면 함께 저장
    tagged_at = datetime.now(timezone.utc).isoformat()
    rows = [
        {"arxiv_id": p["arxiv_id"], "tags": p.get("tags", []), "tagged_at": tagged_at}
        for p in papers
        if p.get("arxiv_id") and p.get("tags")
    ]
    if rows:
        try:
            sb.table("paper_tags").upsert(rows, on_conflict="arxiv_id").execute()
            print(f"  ✔ paper_tags {len(rows)}건 저장")
        except Exception as e:
            print(f"  ⚠ paper_tags 저장 실패 (테이블 없을 수 있음): {e}")

    return updated


def main():
    parser = argparse.ArgumentParser()
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--days", type=int, default=31, help="최근 N일치 처리 (기본 31)")
    grp.add_argument("--all", action="store_true", help="전체 history")
    args = parser.parse_args()

    groq_key = os.environ.get("GROQ_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not all([groq_key, supabase_url, service_key]):
        print("환경변수 필요: GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY")
        sys.exit(1)

    sb = create_client(supabase_url, service_key)

    if args.all:
        since = "2000-01-01"
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"=== 재태깅 시작 ({since} 이후) ===")
    rows = fetch_digests(sb, since)
    print(f"대상 digest: {len(rows)}개\n")

    total_updated = 0
    for row in rows:
        print(f"[{row['date']}]")
        n = retag_digest(sb, row, groq_key)
        total_updated += n
        print()

    print(f"=== 완료: 총 {total_updated}개 논문 재태깅 ===")


if __name__ == "__main__":
    main()
