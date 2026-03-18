"use client";

import { useState } from "react";

export default function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setMessage("");

    const res = await fetch("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json();

    if (res.ok) {
      setStatus("success");
      setMessage("구독 완료! 매일 오전 10시에 논문 다이제스트를 받으실 수 있습니다. 📬");
      setEmail("");
    } else {
      setStatus("error");
      setMessage(data.error ?? "오류가 발생했습니다. 다시 시도해 주세요.");
    }
  }

  return (
    <div className="bg-black text-white rounded-lg px-6 py-5">
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1">
          <h2 className="text-base font-bold mb-0.5">
            매일 아침 AI 논문 받아보기
          </h2>
          <p className="text-gray-400 text-xs">
            HuggingFace 트렌딩 논문을 한국어 요약 + 피규어와 함께 이메일로 드립니다.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2 md:w-[400px]">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="이메일 주소 입력"
            required
            className="flex-1 px-4 py-2 rounded bg-gray-800 text-white
                       placeholder-gray-500 border border-gray-700 text-sm
                       focus:outline-none focus:border-gray-400 transition-colors"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="px-5 py-2 bg-white text-black font-bold rounded text-sm
                       hover:bg-gray-100 disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            {status === "loading" ? "처리중…" : "구독하기"}
          </button>
        </form>
      </div>

      {message && (
        <p
          className={`mt-3 text-sm ${
            status === "success" ? "text-green-400" : "text-red-400"
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
