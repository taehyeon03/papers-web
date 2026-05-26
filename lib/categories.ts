export interface Category {
  key: string;
  label: string;
  color: string;
}

export const CATEGORIES: Category[] = [
  { key: "foundation", label: "파운데이션·LLM", color: "bg-slate-100 text-slate-800 border-slate-300" },
  { key: "nlp", label: "자연어처리", color: "bg-blue-50 text-blue-700 border-blue-200" },
  { key: "vision", label: "비전", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { key: "generative", label: "생성·디퓨전", color: "bg-pink-50 text-pink-700 border-pink-200" },
  { key: "multimodal", label: "멀티모달·월드모델", color: "bg-purple-50 text-purple-700 border-purple-200" },
  { key: "agent", label: "추론·에이전트·RL", color: "bg-amber-50 text-amber-700 border-amber-200" },
  { key: "robotics", label: "로보틱스", color: "bg-orange-50 text-orange-700 border-orange-200" },
  { key: "efficient", label: "효율·시스템", color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  { key: "safety", label: "안전·정렬·해석", color: "bg-rose-50 text-rose-700 border-rose-200" },
  { key: "theory", label: "이론·평가·응용", color: "bg-teal-50 text-teal-700 border-teal-200" },
];

export const CATEGORY_MAP: Record<string, Category> = Object.fromEntries(
  CATEGORIES.map((c) => [c.key, c])
);
