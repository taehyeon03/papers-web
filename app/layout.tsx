import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HuggingFace Papers — 매일 AI 논문 다이제스트",
  description:
    "HuggingFace 트렌딩 논문을 매일 한국어로 요약해서 이메일로 드립니다.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-white text-gray-900 antialiased">{children}</body>
    </html>
  );
}
