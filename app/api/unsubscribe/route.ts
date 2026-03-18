import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const token = req.nextUrl.searchParams.get("token");

  if (!token) {
    return new NextResponse("잘못된 링크입니다.", { status: 400 });
  }

  const { error } = await supabaseAdmin
    .from("subscribers")
    .update({ active: false })
    .eq("token", token);

  if (error) {
    return new NextResponse("오류가 발생했습니다.", { status: 500 });
  }

  return new NextResponse(
    `<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>구독 취소</title></head>
<body style="font-family:sans-serif;text-align:center;padding:80px 20px;color:#333;">
  <h1 style="font-size:24px;margin-bottom:12px;">구독이 취소되었습니다.</h1>
  <p style="color:#888;">더 이상 AI 논문 다이제스트를 받지 않으실 수 있습니다.</p>
  <a href="/" style="display:inline-block;margin-top:24px;color:#000;text-decoration:underline;">
    홈으로 돌아가기
  </a>
</body>
</html>`,
    { headers: { "Content-Type": "text/html; charset=utf-8" } }
  );
}
