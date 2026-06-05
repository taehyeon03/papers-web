import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { supabaseAdmin } from "@/lib/supabase";

export async function POST(req: NextRequest) {
  const { email } = await req.json();

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json(
      { error: "유효한 이메일 주소를 입력해주세요." },
      { status: 400 }
    );
  }

  const { error } = await supabaseAdmin.from("subscribers").upsert(
    { email, token: randomUUID(), active: true },
    { onConflict: "email" }
  );

  if (error) {
    console.error("Subscribe error:", error);
    return NextResponse.json(
      { error: "구독 처리 중 오류가 발생했습니다." },
      { status: 500 }
    );
  }

  return NextResponse.json({ success: true });
}
