import type { Paper } from "@/app/page";

function parseSummary(text: string) {
  const sections: { title: string; lines: string[] }[] = [];
  let current: { title: string; lines: string[] } | null = null;

  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("[") && line.endsWith("]")) {
      if (current) sections.push(current);
      current = { title: line.slice(1, -1), lines: [] };
    } else if (current) {
      current.lines.push(line);
    }
  }
  if (current) sections.push(current);
  return sections;
}

export default function PaperCard({
  paper,
  index,
}: {
  paper: Paper;
  index: number;
}) {
  const sections = parseSummary(paper.summary_kr ?? "");

  return (
    <article className="py-8 md:py-10">
      {/* 번호 + 제목 */}
      <div className="flex items-start gap-3 mb-3">
        <span className="text-[44px] md:text-[56px] font-black leading-none text-gray-100 font-serif-kr select-none flex-shrink-0">
          {String(index).padStart(2, "0")}
        </span>
        <div className="pt-1 min-w-0">
          <h2 className="text-lg md:text-xl font-bold font-serif-kr text-gray-900 leading-snug mb-1">
            {paper.title}
          </h2>
          <a
            href={paper.arxiv_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-400 hover:text-blue-500 transition-colors break-all"
          >
            🔗 {paper.arxiv_url}
          </a>
        </div>
      </div>

      {/* 모바일: 세로 / 데스크탑: 2열 */}
      <div className="flex flex-col md:flex-row gap-4 md:gap-6 mt-3">
        {/* 피규어 — 모바일에서 상단 */}
        {paper.figures?.length > 0 && (
          <div className="flex flex-row md:flex-col gap-3 md:gap-4 md:w-64 md:flex-shrink-0 order-first md:order-last">
            {paper.figures.map((fig, i) => (
              <div key={i} className="flex-1 md:flex-none">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={fig.url}
                  alt={fig.caption || `Figure ${i + 1}`}
                  className="w-full rounded border border-gray-200 bg-gray-50"
                  loading="lazy"
                />
                {fig.caption && (
                  <p className="text-[11px] text-gray-400 mt-1 italic leading-tight hidden md:block">
                    ▲ {fig.caption.slice(0, 120)}
                    {fig.caption.length > 120 ? "…" : ""}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 한국어 요약 */}
        <div className="flex-1 min-w-0 bg-gray-50 border-l-4 border-black px-4 md:px-5 py-4">
          {sections.length > 0 ? (
            sections.map((sec, i) => (
              <div key={i} className={i > 0 ? "mt-4" : ""}>
                <h3 className="text-[11px] font-bold tracking-widest text-gray-400 uppercase border-b border-gray-200 pb-1 mb-2">
                  {sec.title}
                </h3>
                <div className="space-y-1">
                  {sec.lines.map((line, j) => (
                    <p
                      key={j}
                      className={`text-sm leading-relaxed ${
                        line.startsWith("•")
                          ? "text-gray-700 pl-2"
                          : "text-gray-600"
                      }`}
                    >
                      {line}
                    </p>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-400">요약 없음</p>
          )}
        </div>
      </div>
    </article>
  );
}
