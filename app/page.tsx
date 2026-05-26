import { supabase } from "@/lib/supabase";
import PaperCard from "@/components/PaperCard";
import TagSidebar from "@/components/TagSidebar";
import { CATEGORIES } from "@/lib/categories";

export const revalidate = 60;

export interface Figure {
  url: string;
  caption: string;
}

export interface Paper {
  title: string;
  hf_url: string;
  arxiv_url: string;
  arxiv_id: string;
  abstract: string;
  summary_kr: string;
  figures: Figure[];
  tags?: string[];
}

interface DigestRow {
  date: string;
  papers: Paper[] | { papers?: Paper[] } | null;
}

function unwrapPapers(raw: DigestRow["papers"]): Paper[] {
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === "object" && Array.isArray((raw as any).papers)) {
    return (raw as any).papers;
  }
  return [];
}

export default async function Home() {
  const [{ data: digests }, { data: tagRows }] = await Promise.all([
    supabase
      .from("digests")
      .select("date, papers")
      .order("date", { ascending: false }),
    supabase
      .from("paper_tags")
      .select("arxiv_id, tags"),
  ]);

  const all: DigestRow[] = Array.isArray(digests) ? digests : [];

  // arxiv_id → tags 매핑 (paper_tags 테이블이 권위)
  const tagsByArxiv: Record<string, string[]> = {};
  if (Array.isArray(tagRows)) {
    for (const r of tagRows as Array<{ arxiv_id: string; tags: unknown }>) {
      if (r.arxiv_id && Array.isArray(r.tags)) {
        tagsByArxiv[r.arxiv_id] = r.tags as string[];
      }
    }
  }

  const resolveTags = (p: Paper): string[] => {
    if (p.arxiv_id && tagsByArxiv[p.arxiv_id]) return tagsByArxiv[p.arxiv_id];
    return Array.isArray(p.tags) ? p.tags : [];
  };

  // 가장 최근 비어있지 않은 digest를 화면에 표시 (paper_tags의 태그 병합)
  let displayed: { date: string; papers: Paper[] } | null = null;
  for (const row of all) {
    const ps = unwrapPapers(row.papers);
    if (ps.length > 0) {
      displayed = {
        date: row.date,
        papers: ps.map((p) => ({ ...p, tags: resolveTags(p) })),
      };
      break;
    }
  }
  const papers: Paper[] = displayed?.papers ?? [];
  const dateStr = displayed?.date
    ? new Date(displayed.date).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
      })
    : "로딩 중...";

  // 누적 태그 카운트 — paper_tags 테이블 권위
  const counts: Record<string, number> = Object.fromEntries(
    CATEGORIES.map((c) => [c.key, 0])
  );
  let totalTagged = 0;
  for (const tags of Object.values(tagsByArxiv)) {
    if (tags.length === 0) continue;
    totalTagged++;
    for (const t of tags) {
      if (t in counts) counts[t]++;
    }
  }

  return (
    <main className="min-h-screen bg-white">
      <header className="border-t-[5px] border-black">
        <div className="max-w-7xl mx-auto px-6 py-6 text-center">
          <p className="text-[10px] tracking-[4px] text-gray-400 uppercase mb-1">
            Daily AI Research Digest
          </p>
          <h1 className="text-5xl md:text-6xl font-black font-serif-kr text-black leading-tight mb-3">
            HuggingFace Papers
          </h1>
          <div className="border-t border-b border-gray-300 py-2 flex flex-col md:flex-row md:justify-between items-center gap-1 text-[11px] text-gray-500">
            <span>{dateStr}</span>
            <span className="font-semibold">오늘의 AI 논문 upvote 상위 {papers.length}선</span>
            <span>Powered by Groq / Llama 3.3</span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:grid lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-10">
        {/* 좌측 사이드바 — 데스크탑에서만 */}
        <aside className="hidden lg:block">
          <div className="sticky top-4 pt-6">
            <TagSidebar counts={counts} total={totalTagged} />
          </div>
        </aside>

        {/* 논문 목록 */}
        <div className="min-w-0">
          {papers.length === 0 ? (
            <div className="py-24 text-center text-gray-400">
              <p className="text-lg">아직 오늘의 논문이 없습니다.</p>
              <p className="text-sm mt-2">매일 오전 9시에 업데이트됩니다.</p>
            </div>
          ) : (
            <div className="divide-y-2 divide-black">
              {papers.map((paper, i) => (
                <PaperCard key={i} paper={paper} index={i + 1} />
              ))}
            </div>
          )}
        </div>
      </div>

      <footer className="mt-16 border-t border-gray-200 bg-gray-50 py-8 text-center">
        <p className="text-xs text-gray-400">
          자동 생성 · HuggingFace Trending Papers · 매일 오전 9시 업데이트
        </p>
      </footer>
    </main>
  );
}
