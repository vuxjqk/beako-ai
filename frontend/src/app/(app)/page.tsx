"use client";

import { ArrowUp } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { LogoMark, SLOGAN } from "@/components/logo";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const { user } = useAuth();
  const firstName = user.fullName.trim().split(/\s+/).at(-1);

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl">
        <div className="mb-8 flex flex-col items-center text-center">
          <LogoMark className="mb-5 size-10" />
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Xin chào, {firstName}</h1>
          <p className="mt-2 text-muted-foreground">Hôm nay bạn muốn tìm hiểu điều gì?</p>
        </div>

        {/* Chat isn't wired up yet; the composer only previews the layout */}
        <div className="rounded-2xl border bg-card p-3">
          <textarea
            rows={3}
            disabled
            placeholder="Hỏi Beako bất cứ điều gì…"
            className="w-full resize-none bg-transparent px-1 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Tính năng trò chuyện sắp ra mắt</span>
            <Button size="icon" disabled aria-label="Gửi">
              <ArrowUp />
            </Button>
          </div>
        </div>
        <p className="mt-4 text-center text-xs text-muted-foreground">Beako AI · {SLOGAN}</p>
      </div>
    </main>
  );
}
