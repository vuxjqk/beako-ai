"use client";

import { ArrowUp, CircleAlert, EyeOff, SquarePen } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ChatTurn, type Turn } from "@/components/chat/chat-turn";
import { describe, type Step } from "@/components/chat/progress-steps";
import { conversationIdFromPath, useConversations } from "@/components/conversations-provider";
import { LogoMark, SLOGAN } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { askStream, MAX_VOLUME, qaApi, type StatusEvent, type StoredTurn } from "@/lib/qa";

const SPOILER_KEY = "beako.maxVolume";
const MAX_QUESTION = 1000;
// While a loaded conversation still has a question being answered, re-read it this often
const WAITING_POLL_MS = 3000;
// A question unanswered for longer than this was lost (the server gives up long before)
const WAITING_GIVE_UP_MS = 10 * 60 * 1000;
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

/** "sau 45 giây" / "sau 3 phút" / "vào ngày mai" for a Retry-After in seconds. */
function waitText(seconds: number | undefined): string {
  if (!seconds) return "sau ít phút";
  if (seconds < 60) return `sau ${seconds} giây`;
  if (seconds < 3600) return `sau ${Math.ceil(seconds / 60)} phút`;
  return "vào ngày mai";
}

/** Vietnamese message for a failed question, by the backend's reason code (see POST /qa). */
function askErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "input_rejected":
        return "Câu hỏi này trông như đang cố thay đổi chỉ dẫn của trợ lý nên không được xử lý. Hãy hỏi về nội dung truyện.";
      case "busy":
        return "Câu hỏi trước của bạn vẫn đang được trả lời. Vui lòng đợi nó xong rồi hỏi tiếp.";
      case "rate_limited":
        return `Bạn hỏi hơi nhanh. Vui lòng thử lại ${waitText(error.retryAfter)}.`;
      case "user_quota":
        return "Bạn đã dùng hết lượt hỏi của hôm nay. Hạn mức sẽ được làm mới vào ngày mai.";
      case "budget":
        return "Hệ thống đã đạt giới hạn sử dụng của hôm nay. Vui lòng quay lại vào ngày mai.";
      case "llm_quota":
        return "Dịch vụ AI đã hết hạn mức. Vui lòng thử lại sau.";
      case "llm_rate_limited":
      case "llm_unavailable":
        return "Dịch vụ AI đang quá tải hoặc tạm thời gián đoạn. Vui lòng thử lại sau ít phút.";
      case "llm_timeout":
        return "Dịch vụ AI phản hồi quá lâu. Vui lòng thử lại.";
      case "llm_empty":
        return "Dịch vụ AI trả về câu trả lời rỗng. Vui lòng hỏi lại.";
      case "llm_not_configured":
        return "Tính năng hỏi đáp chưa được cấu hình trên máy chủ.";
    }
  }
  return errorMessage(error, {
    404: "Cuộc trò chuyện không còn tồn tại. Hãy bắt đầu cuộc trò chuyện mới.",
    502: "Dịch vụ AI không trả lời được. Vui lòng thử lại sau ít phút.",
  });
}

/** A question from history as a chat turn; agent tool calls become its "searched N times" steps. */
function fromStored(t: StoredTurn, index: number): Turn {
  const startedAt = new Date(t.askedAt).getTime();
  const base = { id: `stored-${index}`, question: t.question, maxVolume: t.maxVolume, startedAt };
  if (t.answer) {
    const steps = t.answer.trace
      .filter((e) => "tool" in e)
      .map((e) => describe({ type: "tool", ...e } as StatusEvent))
      .filter((step): step is Step => step !== null);
    const ms = (t.answer.timingsMs.retrieval ?? 0) + (t.answer.timingsMs.llm ?? 0);
    return { ...base, status: "done", steps, seconds: ms / 1000, answer: t.answer, feedback: t.feedback };
  }
  if (t.error) {
    return {
      ...base,
      status: "error",
      steps: [],
      seconds: 0,
      error:
        t.error === "cancelled"
          ? "Câu trả lời đã bị dừng vì bạn rời trang trước khi trả lời xong."
          : "Không trả lời được câu hỏi này.",
    };
  }
  if (Date.now() - startedAt > WAITING_GIVE_UP_MS) {
    return { ...base, status: "error", steps: [], seconds: 0, error: "Câu hỏi này không có câu trả lời." };
  }
  return { ...base, status: "waiting", steps: [], seconds: 0 };
}

function saveSpoilerLimit(value: number | null) {
  try {
    if (value === null) localStorage.removeItem(SPOILER_KEY);
    else localStorage.setItem(SPOILER_KEY, String(value));
  } catch {
    // Private mode / storage blocked: the choice just won't be remembered
  }
}

/**
 * Question answering over the novels. "/" starts a new conversation; "/c/<id>" shows a stored
 * one. A new conversation moves to its own URL as soon as the server creates it, without
 * remounting, so the answer in progress keeps streaming.
 */
export function ChatView() {
  const { user } = useAuth();
  const { touch } = useConversations();
  const firstName = user.fullName.trim().split(/\s+/).at(-1);
  const pathname = usePathname();
  const routeId = conversationIdFromPath(pathname);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  // The stored conversation being loaded, and why loading failed
  const [loading, setLoading] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [maxVolume, setMaxVolume] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // The conversation on screen, readable from stream callbacks that outlive a switch
  const shownRef = useRef<string | null>(null);
  // Bumped on every switch, so a question asked before it no longer touches the screen
  const viewRef = useRef(0);
  const pending = turns.some((t) => t.status === "pending");
  const waiting = turns.some((t) => t.status === "waiting");

  // localStorage only exists in the browser; read it after the first render
  useEffect(() => setMaxVolume(readSpoilerLimit()), []);

  const load = useCallback(async (id: string, quiet = false) => {
    if (!quiet) setLoading(id);
    try {
      const detail = await qaApi.conversation(id);
      if (shownRef.current !== id) return;
      setTurns(detail.turns.map(fromStored));
      setLoadError(null);
    } catch (error) {
      if (shownRef.current !== id || quiet) return;
      setLoadError(errorMessage(error, { 404: "Không tìm thấy cuộc trò chuyện này. Có thể nó đã bị xóa." }));
    } finally {
      if (!quiet) setLoading((current) => (current === id ? null : current));
    }
  }, []);

  // Follow the URL: "/" = a new conversation, "/c/<id>" = load it. Our own move from "/" to the
  // new conversation's URL is already on screen and changes nothing. A question still being
  // answered when the user switches keeps running on the server and lands in its conversation.
  useEffect(() => {
    if (routeId === shownRef.current) return;
    shownRef.current = routeId;
    viewRef.current += 1;
    setConversationId(routeId);
    setTurns([]);
    setInput("");
    setLoadError(null);
    if (routeId) load(routeId);
  }, [routeId, load]);

  // A question still being answered (another tab, or this one before a reload): check back
  useEffect(() => {
    if (!waiting || !conversationId) return;
    const timer = setInterval(() => load(conversationId, true), WAITING_POLL_MS);
    return () => clearInterval(timer);
  }, [waiting, conversationId, load]);

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

  async function ask(text: string, volumeLimit: number | null = maxVolume) {
    const question = text.trim();
    if (question.length < 3 || pending || waiting) return;
    const id = crypto.randomUUID();
    const startedAt = Date.now();
    const view = viewRef.current;
    const onScreen = () => viewRef.current === view;
    setTurns((all) => [
      ...all,
      { id, question, maxVolume: volumeLimit, status: "pending", steps: [], startedAt, seconds: 0 },
    ]);
    setInput("");
    try {
      const answer = await askStream(
        { question, maxVolume: volumeLimit, conversationId },
        {
          onStart: ({ conversationId: cid }) => {
            touch({ id: cid, title: question });
            if (!onScreen() || shownRef.current === cid) return;
            // A new conversation: give it its URL (and history entry) without remounting
            shownRef.current = cid;
            setConversationId(cid);
            window.history.replaceState(null, "", `/c/${cid}`);
          },
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
        error: askErrorMessage(error),
      }));
    } finally {
      if (onScreen()) textareaRef.current?.focus();
    }
  }

  function newConversation() {
    // "/" and "/c/<id>" share this component: going to "/" resets it through the URL effect
    if (routeId) {
      window.history.pushState(null, "", "/");
    } else {
      shownRef.current = null;
      viewRef.current += 1;
      setTurns([]);
      setConversationId(null);
      setInput("");
    }
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
        <Button
          type="submit"
          size="icon"
          disabled={pending || waiting || input.trim().length < 3}
          aria-label="Gửi"
        >
          <ArrowUp />
        </Button>
      </div>
    </form>
  );

  if (routeId && loadError) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12 text-center">
        <CircleAlert className="size-8 text-muted-foreground" />
        <p className="max-w-sm text-sm text-muted-foreground">{loadError}</p>
        <Button asChild variant="outline">
          <Link href="/">
            <SquarePen />
            Cuộc trò chuyện mới
          </Link>
        </Button>
      </main>
    );
  }

  if (routeId && (loading === routeId || !turns.length)) {
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 space-y-8 px-4 py-8" aria-busy>
        {[0, 1].map((i) => (
          <div key={i} className="space-y-4">
            <Skeleton className="ml-auto h-10 w-2/5 rounded-2xl" />
            <div className="space-y-2 pl-9">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-3/5" />
            </div>
          </div>
        ))}
      </main>
    );
  }

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
        {turns.map((t, i) => (
          <ChatTurn
            key={t.id}
            turn={t}
            // Only the last question can be asked again, and only while nothing else is running
            onRetry={
              i === turns.length - 1 && !pending && !waiting ? () => ask(t.question, t.maxVolume) : undefined
            }
          />
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="sticky bottom-0 bg-background pt-2 pb-4">{composer}</div>
    </main>
  );
}
