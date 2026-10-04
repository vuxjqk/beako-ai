"use client";

import {
  BookOpen,
  Check,
  ChevronDown,
  List,
  MessageSquareQuote,
  PenLine,
  Search,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { Spinner } from "@/components/ui/spinner";
import type { StatusEvent } from "@/lib/qa";
import { cn } from "@/lib/utils";

export type Step = { icon: LucideIcon; text: string };

function volumes(args: Record<string, unknown>): string {
  if (typeof args.short_story_collection === "number") return ` · Tuyển tập truyện ngắn ${args.short_story_collection}`;
  const list = Array.isArray(args.volumes) ? (args.volumes as number[]).filter(Number.isFinite) : [];
  if (!list.length) return "";
  const sorted = [...list].sort((a, b) => a - b);
  const contiguous = sorted.every((v, i) => i === 0 || v === sorted[i - 1] + 1);
  const label =
    sorted.length === 1
      ? `Tập ${sorted[0]}`
      : contiguous
        ? `Tập ${sorted[0]}–${sorted.at(-1)}`
        : `Tập ${sorted.join(", ")}`;
  return ` · ${label}${typeof args.chapter === "number" ? `, chương ${args.chapter}` : ""}`;
}

function book(args: Record<string, unknown>): string {
  if (typeof args.short_story_collection === "number") return `Tuyển tập truyện ngắn ${args.short_story_collection}`;
  return `Tập ${args.volume ?? "?"}`;
}

/** One visible step for a progress event, or null for events that are not worth showing. */
export function describe(event: StatusEvent): Step | null {
  switch (event.type) {
    case "rewrite":
      return { icon: MessageSquareQuote, text: `Hiểu câu hỏi là “${event.question}”` };
    case "route":
      return event.reason === "simple path found nothing"
        ? { icon: Sparkles, text: "Chưa thấy câu trả lời, đang tra cứu kỹ hơn" }
        : null;
    case "llm":
      if (event.final) return { icon: PenLine, text: "Đang viết câu trả lời" };
      return { icon: Sparkles, text: event.step === 1 ? "Đang phân tích câu hỏi" : "Đang đọc kết quả" };
    case "tool": {
      const a = event.args ?? {};
      if (event.tool === "search") {
        return { icon: Search, text: `Tìm “${String(a.query ?? "")}”${volumes(a)}` };
      }
      if (event.tool === "read_chapter") {
        const page = typeof a.page === "number" && a.page > 1 ? `, trang ${a.page}` : "";
        return { icon: BookOpen, text: `Đọc ${book(a)} · ${String(a.chapter ?? "")}${page}` };
      }
      if (event.tool === "list_chapters") return { icon: List, text: `Xem mục lục ${book(a)}` };
      if (event.tool === "read_around") return { icon: BookOpen, text: `Đọc thêm quanh đoạn [${a.passage ?? "?"}]` };
      return { icon: Search, text: event.tool };
    }
  }
}

/** What the system is doing while an answer is prepared; folds into one line when done. */
export function ProgressSteps({ steps, pending, seconds }: { steps: Step[]; pending: boolean; seconds: number }) {
  const [open, setOpen] = useState(false);
  const searches = steps.filter((s) => s.icon === Search || s.icon === BookOpen || s.icon === List).length;

  if (!pending) {
    if (!steps.length) return null;
    return (
      <div className="text-xs text-muted-foreground">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1 rounded hover:text-foreground"
          aria-expanded={open}
        >
          <ChevronDown className={cn("size-3.5 transition-transform", !open && "-rotate-90")} />
          Đã tra cứu {searches} lần · {seconds.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây
        </button>
        {open && <StepList steps={steps} pending={false} />}
      </div>
    );
  }

  return (
    <div className="text-sm text-muted-foreground" aria-live="polite">
      <StepList steps={steps.length ? steps : [{ icon: Sparkles, text: "Đang bắt đầu" }]} pending />
      <p className="mt-1 pl-6 text-xs tabular-nums">{Math.floor(seconds)} giây</p>
    </div>
  );
}

function StepList({ steps, pending }: { steps: Step[]; pending: boolean }) {
  return (
    <ol className="mt-1.5 space-y-1">
      {steps.map((step, i) => {
        const current = pending && i === steps.length - 1;
        const Icon = step.icon;
        return (
          <li key={i} className={cn("flex items-start gap-2", current && "text-foreground")}>
            <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center">
              {current ? <Spinner className="size-3.5" /> : pending ? <Check className="size-3.5" /> : <Icon className="size-3.5" />}
            </span>
            <span className="min-w-0 break-words">{step.text}</span>
          </li>
        );
      })}
    </ol>
  );
}
