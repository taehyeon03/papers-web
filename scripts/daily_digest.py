"""
HuggingFace Papers Daily Digest
- HuggingFace trending 스크래핑
- arxiv에서 초록 + 메인 피규어 추출
- Groq (Llama 3.3 70B)으로 한국어 요약
- Supabase에 저장 (웹 표시용)
"""

import os
import re
import time
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from groq import Groq
from supabase import create_client

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
HF_TRENDING_URL = "https://huggingface.co/papers"
MAX_PAPERS = 10  # HuggingFace trending 페이지는 upvote 순 정렬 → 상위 10개 수집
MAX_FIGURES_PER_PAPER = 2
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────────
# 1. 논문 목록 수집
# ──────────────────────────────────────────────
def get_trending_papers(limit=MAX_PAPERS):
    resp = requests.get(HF_TRENDING_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    papers, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # /papers/XXXX.XXXXX 형식만 (앵커 없이)
        if not re.match(r"^/papers/\d{4}\.\d+$", href):
            continue
        # 제목 텍스트가 있는 링크만 사용
        title = a.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        hf_url = f"https://huggingface.co{href}"
        if hf_url in seen:
            continue
        seen.add(hf_url)
        papers.append({"title": title, "hf_url": hf_url})
        if len(papers) >= limit:
            break
    return papers


# ──────────────────────────────────────────────
# 2. 논문 상세 (초록 + arxiv ID + 피규어)
# ──────────────────────────────────────────────
def get_paper_details(hf_url):
    resp = requests.get(hf_url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")

    abstract = ""
    for sel in ["div.pb-8 p", "p.text-gray-700", "div[class*='abstract'] p", "section p"]:
        el = soup.select_one(sel)
        if el and len(el.text.strip()) > 80:
            abstract = el.text.strip()
            break

    arxiv_id = None
    for a in soup.find_all("a", href=True):
        m = re.search(r"arxiv\.org/abs/([\d.]+)", a["href"])
        if m:
            arxiv_id = m.group(1)
            break

    figures = _extract_figures(arxiv_id) if arxiv_id else []

    return {
        "abstract": abstract,
        "arxiv_id": arxiv_id,
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else hf_url,
        "figures": figures,
    }


def _extract_figures(arxiv_id):
    """arxiv HTML 버전에서 피규어 추출 → [{"url": ..., "caption": ...}]"""
    base_url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        results, priority = [], []

        for fig in soup.select("figure"):
            img = fig.select_one("img")
            cap_el = fig.select_one("figcaption")
            if not img:
                continue
            src = img.get("src", "")
            if not src or src.startswith("data:"):
                continue
            url = src if src.startswith("http") else urljoin(base_url, src)
            caption = cap_el.text.strip()[:200] if cap_el else ""

            item = {"url": url, "caption": caption}
            if caption and re.search(r"[Ff]ig(ure)?\.?\s*[12]\b", caption):
                priority.append(item)
            else:
                results.append(item)

        combined = priority + results
        return combined[:MAX_FIGURES_PER_PAPER]
    except Exception as e:
        print(f"    피규어 추출 실패: {e}")
        return []


# ──────────────────────────────────────────────
# 3. Gemini 한국어 요약
# ──────────────────────────────────────────────
def summarize_korean(title, abstract, api_key):
    client = Groq(api_key=api_key)
    prompt = f"""아래 AI/ML 논문을 한국어로 분석해줘.

제목: {title}
초록: {abstract}

반드시 아래 형식 그대로 출력해줘 (마크다운 없이):

[핵심 요약]
이 논문이 해결하는 문제와 핵심 아이디어를 2~3문장으로.

[아키텍처 / 방법론]
어떤 구조나 기법을 사용했는지 구체적으로 3~4문장.

[주요 기여 및 결과]
• 기여 또는 성능 결과 1
• 기여 또는 성능 결과 2
• 기여 또는 성능 결과 3"""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                wait = 10 * (attempt + 1)
                print(f"    API 제한, {wait}초 대기…")
                time.sleep(wait)
                continue
            return f"[핵심 요약]\n요약 생성 실패: {e}"
    return "[핵심 요약]\n요약 생성 실패: API 한도 초과"


# ──────────────────────────────────────────────
# 4. Supabase 저장
# ──────────────────────────────────────────────
def save_to_supabase(papers_data, date_str):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    sb.table("digests").upsert(
        {"date": date_str, "papers": papers_data},
        on_conflict="date"
    ).execute()
    print(f"  ✔ Supabase 저장 완료 ({len(papers_data)}개 논문)")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
if __name__ == "__main__":
    today = date.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    today_iso = today.isoformat()
    groq_key = os.environ["GROQ_API_KEY"]

    print("=" * 60)
    print(f"📡 HuggingFace Trending — {today_str}")
    print("=" * 60)

    papers = get_trending_papers()
    print(f"✔ {len(papers)}개 논문 발견\n")

    results = []
    for idx, p in enumerate(papers, 1):
        print(f"[{idx}/{len(papers)}] {p['title'][:60]}")
        details = get_paper_details(p["hf_url"])
        print(f"  arxiv: {details['arxiv_id']} | 피규어: {len(details['figures'])}개")

        if details["abstract"]:
            print("  → Groq 요약 생성 중…")
            summary = summarize_korean(p["title"], details["abstract"], groq_key)
            time.sleep(4)
        else:
            summary = "[핵심 요약]\n초록을 가져올 수 없습니다."

        results.append({**p, **details, "summary_kr": summary})
        print()

    print("💾 Supabase 저장 중…")
    save_to_supabase(results, today_iso)

    print("\n✅ 완료!")
