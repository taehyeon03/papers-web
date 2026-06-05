import { CATEGORIES } from "@/lib/categories";

export default function TagSidebar({
  counts,
  total,
  period,
}: {
  counts: Record<string, number>;
  total: number;
  period: string;
}) {
  const max = Math.max(1, ...Object.values(counts));

  return (
    <div className="text-xs">
      <h3 className="text-[10px] font-bold tracking-widest text-gray-400 uppercase border-b border-gray-200 pb-2 mb-3">
        분야별 누적
      </h3>
      <p className="text-[10px] text-gray-400 mb-1">
        {period} · 매월 1일 리셋
      </p>
      <p className="text-[10px] text-gray-400 mb-3">
        총 <span className="font-bold text-gray-700">{total}</span>편
      </p>
      <ul className="space-y-2">
        {CATEGORIES.map((cat) => {
          const n = counts[cat.key] ?? 0;
          const pct = (n / max) * 100;
          return (
            <li key={cat.key}>
              <div className="flex items-baseline justify-between gap-2 mb-1">
                <span className="text-[11px] text-gray-700 font-medium truncate">
                  {cat.label}
                </span>
                <span className="text-[11px] tabular-nums font-bold text-gray-900 flex-shrink-0">
                  {n}
                </span>
              </div>
              <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gray-700"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
