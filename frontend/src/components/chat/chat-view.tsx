"use client";

import { ArrowUp, EyeOff, SquarePen } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ChatTurn, type Turn } from "@/components/chat/chat-turn";
import { describe } from "@/components/chat/progress-steps";
import { LogoMark, SLOGAN } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { errorMessage } from "@/lib/errors";
import { askStream, MAX_VOLUME } from "@/lib/qa";

const SPOILER_KEY = "beako.maxVolume";
const MAX_QUESTION = 1000;
const EXAMPLES = [
  "Ai đã giết Cá Voi Trắng?",
  "Tóm tắt những gì xảy ra ở Thánh Địa.",
  "Rem và Ram có quan hệ gì?",
];

function readSpoilerLimit(): number | null {
  try {
    const n = Number(localStorage.getItem(SPOILER_KEY));
    return Number.isInteger(n) && n >= 1 && n <= MAX_VOLUME ? n : null;
  } catch {
    return null;
  }
}

function saveSpoilerLimit(value: number | null) {
  try {
    if (value === null) localStorage.removeItem(SPOILER_KEY);
    else localStorage.setItem(SPOILER_KEY, String(value));
  } catch {
    // Private mode / storage blocked: the choice just won't be remembered
  }
}

/** Question answering over the novels: one conversation per page visit, no history yet. */
export function ChatView() {
  const { user } = useAuth();
  const firstName = user.fullName.trim().split(/\s+/).at(-1);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [maxVolume, setMaxVolume] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pending = turns.some((t) => t.status === "pending");

  // localStorage only exists in the browser; read it after the first render
  useEffect(() => setMaxVolume(readSpoilerLimit()), []);

  // Tick the elapsed time of the pending answer
  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(() => {
      setTurns((all) =>
        all.map((t) => (t.status === "pending" ? { ...t, seconds: (Date.now() - t.startedAt) / 1000 } : t)),
      );
    }, 500);
    return () => clearInterval(timer);
  }, [pending]);

  const lastStepCount = turns.at(-1)?.steps.length;
  const lastStatus = turns.at(-1)?.status;
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, lastStepCount, lastStatus]);

  const update = useCallback((id: string, change: (t: Turn) => Turn) => {
    setTurns((all) => all.map((t) => (t.id === id ? change(t) : t)));
  }, []);

  async function ask(text: string) {
    const question = text.trim();
    if (question.length < 3 || pending) return;
    const id = crypto.randomUUID();
    const startedAt = Date.now();
    setTurns((all) => [
      ...all,
      { id, question, maxVolume, status: "pending", steps: [], startedAt, seconds: 0 },
    ]);
    setInput("");
    try {
      const answer = await askStream(
        { question, maxVolume, conversationId },
        {
          onStart: ({ conversationId: cid }) => setConversationId(cid),
          onStatus: (event) => {
            const step = describe(event);
            if (step) update(id, (t) => ({ ...t, steps: [...t.steps, step] }));
          },
        },
      );
      update(id, (t) => ({ ...t, status: "done", answer, seconds: (Date.now() - startedAt) / 1000 }));
    } catch (error) {
      update(id, (t) => ({
        ...t,
        status: "error",
        seconds: (Date.now() - startedAt) / 1000,
        error: errorMessage(error, {
          502: "Dịch vụ AI đang quá tải hoặc đã hết hạn mức. Vui lòng thử lại sau ít phút.",
          503: "Tính năng hỏi đáp chưa được cấu hình trên máy chủ.",
          404: "Cuộc trò chuyện không còn tồn tại. Hãy bắt đầu cuộc trò chuyện mới.",
        }),
      }));
    } finally {
      textareaRef.current?.focus();
    }
  }

  function newConversation() {
    setTurns([]);
    setConversationId(null);
    setInput("");
    textareaRef.current?.focus();
  }

  const composer = (
    <form
      className="rounded-2xl border bg-card p-3 shadow-xs"
      onSubmit={(e) => {
        e.preventDefault();
        ask(input);
      }}
    >
      <textarea
        ref={textareaRef}
        rows={turns.length ? 2 : 3}
        value={input}
        maxLength={MAX_QUESTION}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          // Enter sends, Shift+Enter breaks the line; never while an IME (Vietnamese Telex) is composing
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            ask(input);
          }
        }}
        placeholder="Hỏi Beako về Re:ZERO, bằng tiếng Việt hoặc tiếng Anh…"
        aria-label="Câu hỏi"
        className="w-full resize-none bg-transparent px-1 text-sm outline-none placeholder:text-muted-foreground"
      />
      <div className="flex items-center justify-between gap-2">
        <Select
          value={maxVolume === null ? "all" : String(maxVolume)}
          onValueChange={(value) => {
            const next = value === "all" ? null : Number(value);
            setMaxVolume(next);
            saveSpoilerLimit(next);
          }}
        >
          <SelectTrigger size="sm" className="w-auto gap-1.5 text-xs" aria-label="Chống tiết lộ nội dung">
            <EyeOff className="size-3.5" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Không giới hạn (đã đọc hết)</SelectItem>
            {Array.from({ length: MAX_VOLUME }, (_, i) => i + 1).map((n) => (
              <SelectItem key={n} value={String(n)}>
                Đã đọc đến Tập {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button type="submit" size="icon" disabled={pending || input.trim().length < 3} aria-label="Gửi">
          <ArrowUp />
        </Button>
      </div>
    </form>
  );

  if (!turns.length) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-2xl">
          <div className="mb-8 flex flex-col items-center text-center">
            <LogoMark className="mb-5 size-10" />
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Xin chào, {firstName}</h1>
            <p className="mt-2 text-muted-foreground">Hôm nay bạn muốn tìm hiểu điều gì về Re:ZERO?</p>
          </div>
          {composer}
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => ask(q)}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                {q}
              </button>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            Beako AI · {SLOGAN}. Chọn “Đã đọc đến Tập N” để không bị tiết lộ nội dung các tập sau.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4">
      <div className="flex justify-end pt-3">
        <Button variant="ghost" size="sm" onClick={newConversation} disabled={pending}>
          <SquarePen />
          Cuộc trò chuyện mới
        </Button>
      </div>
      <div className="flex-1 space-y-8 py-4">
        {turns.map((t) => (
          <ChatTurn key={t.id} turn={t} />
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="sticky bottom-0 bg-background pt-2 pb-4">{composer}</div>
    </main>
  );
}
