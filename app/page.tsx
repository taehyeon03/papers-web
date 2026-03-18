import { supabase } from "@/lib/supabase";
import SubscribeForm from "@/components/SubscribeForm";
import PaperCard from "@/components/PaperCard";

export const revalidate = 60; // 1시간마다 재빌드

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
}

export default async function Home() {
  const { data: digest } = await supabase
    .from("digests")
    .select("date, papers")
    .order("date", { ascending: false })
    .limit(1)
    .single();

  const papers: Paper[] = digest?.papers ?? [];
  const dateStr = digest?.date
    ? new Date(digest.date).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
      })
    : "로딩 중...";

  return (
    <main className="min-h-screen bg-white">
      {/* ── 신문 헤더 ── */}
      <header className="border-t-[5px] border-black">
        <div className="max-w-5xl mx-auto px-6 py-6 text-center">
          <p className="text-[10px] tracking-[4px] text-gray-400 uppercase mb-1">
            Daily AI Research Digest
          </p>
          <h1 className="text-5xl md:text-6xl font-black font-serif-kr text-black leading-tight mb-3">
            HuggingFace Papers
          </h1>
          <div className="border-t border-b border-gray-300 py-2 flex flex-col md:flex-row md:justify-between items-center gap-1 text-[11px] text-gray-500">
            <span>{dateStr}</span>
            <span className="font-semibold">오늘의 AI 논문 {papers.length}선</span>
            <span>Powered by Groq / Llama 3.3</span>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 md:px-6">
        {/* ── 구독 폼 ── */}
        <div className="my-8">
          <SubscribeForm />
        </div>

        {/* ── 논문 목록 ── */}
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

      {/* ── 푸터 ── */}
      <footer className="mt-16 border-t border-gray-200 bg-gray-50 py-8 text-center">
        <p className="text-xs text-gray-400">
          자동 생성 · HuggingFace Trending Papers · 매일 오전 9시 업데이트
        </p>
      </footer>
    </main>
  );
}
