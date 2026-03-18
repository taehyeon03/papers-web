"""
HuggingFace Papers Daily Digest
- HuggingFace trending 스크래핑
- arxiv에서 초록 + 메인 피규어 추출
- Gemini Flash로 한국어 요약
- Supabase에 저장 (웹 표시용)
- 구독자 전체에게 신문 형식 이메일 발송
"""

import os
import re
import time
import smtplib
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types as genai_types
from supabase import create_client
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
HF_TRENDING_URL = "https://huggingface.co/papers"
MAX_PAPERS = 8
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
    client = genai.Client(api_key=api_key)
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
    for model in ["gemini-2.0-flash", "gemini-2.5-flash"]:
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                err = str(e)
                if "503" in err or "UNAVAILABLE" in err:
                    time.sleep(5 * (attempt + 1))
                    continue
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    wait = 30 * (attempt + 1)
                    print(f"    속도 제한, {wait}초 대기 후 재시도…")
                    time.sleep(wait)
                    continue
                return f"[핵심 요약]\n요약 생성 실패: {e}"
    return "[핵심 요약]\n요약 생성 실패: 모든 재시도 실패"


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


def get_subscribers():
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("subscribers").select("email, token").eq("active", True).execute()
    return result.data or []


# ──────────────────────────────────────────────
# 5. 이메일 HTML 생성 (신문 형식)
# ──────────────────────────────────────────────
def fmt_summary_html(text):
    """요약 텍스트 → 섹션별 HTML"""
    html_parts = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("[") and s.endswith("]"):
            html_parts.append(
                f'<p style="margin:14px 0 5px;font-size:11px;font-weight:700;'
                f'color:#555;letter-spacing:1px;text-transform:uppercase;'
                f'border-bottom:1px solid #e0e0e0;padding-bottom:4px;">'
                f'{s[1:-1]}</p>'
            )
        elif s.startswith("•"):
            html_parts.append(
                f'<p style="margin:3px 0;font-size:14px;color:#333;'
                f'padding-left:10px;line-height:1.7;">{s}</p>'
            )
        else:
            html_parts.append(
                f'<p style="margin:4px 0;font-size:14px;color:#444;line-height:1.8;">{s}</p>'
            )
    return "\n".join(html_parts)


def build_email_html(papers_data, date_str, unsub_token, site_url):
    unsub_url = f"{site_url}/api/unsubscribe?token={unsub_token}"

    articles = ""
    for i, p in enumerate(papers_data, 1):
        figs_html = ""
        for fig in p.get("figures", []):
            cap = fig["caption"][:120] + "…" if len(fig["caption"]) > 120 else fig["caption"]
            figs_html += f"""
            <tr><td style="padding:4px 0;">
              <img src="{fig['url']}" alt="figure"
                   style="max-width:260px;width:100%;border-radius:4px;
                          border:1px solid #e8e8e8;display:block;" />
              {'<p style="margin:3px 0 0;font-size:11px;color:#999;font-style:italic;">▲ ' + cap + '</p>' if cap else ''}
            </td></tr>"""

        fig_col = (
            f'<td width="270" valign="top" style="padding-left:20px;">'
            f'<table cellpadding="0" cellspacing="0" border="0">{figs_html}</table></td>'
            if figs_html else ""
        )

        articles += f"""
        <tr><td style="padding:0 0 36px;border-bottom:2px solid #111;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td width="56" valign="top"
                  style="font-size:52px;font-weight:900;color:#ececec;
                         font-family:Georgia,serif;line-height:1;padding-right:10px;">
                {i:02d}
              </td>
              <td valign="top">
                <p style="margin:0 0 3px;font-size:18px;font-weight:800;color:#111;
                          font-family:Georgia,serif;line-height:1.3;">{p['title']}</p>
                <p style="margin:0 0 14px;font-size:12px;">
                  <a href="{p['arxiv_url']}" style="color:#999;text-decoration:none;">
                    🔗 {p['arxiv_url']}
                  </a>
                </p>
              </td>
            </tr>
            <tr><td colspan="2">
              <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
                <td valign="top">
                  <div style="background:#f9f9f9;border-left:4px solid #111;padding:14px 18px;border-radius:0 6px 6px 0;">
                    {fmt_summary_html(p.get('summary_kr', ''))}
                  </div>
                </td>
                {fig_col}
              </tr></table>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="height:36px;"></td></tr>
        """

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#fff;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fff;">
<tr><td align="center">
<table width="840" cellpadding="0" cellspacing="0" border="0" style="max-width:840px;width:100%;">

  <!-- 헤더 -->
  <tr><td style="border-top:5px solid #111;border-bottom:1px solid #ccc;padding:22px 36px 16px;text-align:center;">
    <p style="margin:0 0 3px;font-size:10px;color:#aaa;letter-spacing:3px;text-transform:uppercase;">Daily AI Research Digest</p>
    <h1 style="margin:0 0 10px;font-size:42px;font-weight:900;color:#111;font-family:Georgia,serif;letter-spacing:-1px;">HuggingFace Papers</h1>
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #ddd;padding-top:8px;margin-top:4px;">
      <tr>
        <td style="font-size:11px;color:#888;text-align:left;">{date_str} · KST</td>
        <td style="font-size:11px;color:#888;text-align:center;">오늘의 AI 논문 {len(papers_data)}선</td>
        <td style="font-size:11px;color:#888;text-align:right;">Powered by Gemini 1.5 Flash</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="height:32px;"></td></tr>

  <!-- 논문 본문 -->
  <tr><td style="padding:0 36px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      {articles}
    </table>
  </td></tr>

  <!-- 푸터 -->
  <tr><td style="border-top:1px solid #e0e0e0;padding:18px 36px;background:#f5f5f5;text-align:center;">
    <p style="margin:0 0 6px;font-size:11px;color:#bbb;">자동 생성 AI 논문 다이제스트 · HuggingFace Trending Papers</p>
    <p style="margin:0;font-size:11px;">
      <a href="{site_url}" style="color:#999;">웹에서 보기</a>
      &nbsp;·&nbsp;
      <a href="{unsub_url}" style="color:#999;">구독 취소</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


# ──────────────────────────────────────────────
# 6. 이메일 발송
# ──────────────────────────────────────────────
def send_emails(papers_data, subscribers, date_str, site_url):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pw = os.environ["GMAIL_PASSWORD"]
    subject = f"[AI 논문 다이제스트] {date_str} — HuggingFace Trending {len(papers_data)}선"

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pw)
        for sub in subscribers:
            html = build_email_html(papers_data, date_str, sub["token"], site_url)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"AI Papers Digest <{gmail_user}>"
            msg["To"] = sub["email"]
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(gmail_user, sub["email"], msg.as_string())
            print(f"  → {sub['email']}")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
if __name__ == "__main__":
    today = date.today()
    today_str = today.strftime("%Y년 %m월 %d일")
    today_iso = today.isoformat()
    gemini_key = os.environ["GEMINI_API_KEY"]
    site_url = os.environ.get("SITE_URL", "https://your-app.vercel.app").rstrip("/")

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
            print("  → Gemini 요약 생성 중…")
            summary = summarize_korean(p["title"], details["abstract"], gemini_key)
            time.sleep(4)
        else:
            summary = "[핵심 요약]\n초록을 가져올 수 없습니다."

        results.append({**p, **details, "summary_kr": summary})
        print()

    print("💾 Supabase 저장 중…")
    save_to_supabase(results, today_iso)

    print("\n📬 구독자 조회 중…")
    subscribers = get_subscribers()
    print(f"  → {len(subscribers)}명")

    if subscribers:
        print("📮 이메일 발송 중…")
        send_emails(results, subscribers, today_str, site_url)
    else:
        print("  구독자 없음, 발송 생략")

    print("\n✅ 완료!")
