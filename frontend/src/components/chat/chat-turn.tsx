"use client";

import { CircleAlert, EyeOff, Loader, RotateCw } from "lucide-react";
import { useMemo, useState } from "react";

import { AnswerBody } from "@/components/chat/answer-body";
import { FeedbackBar } from "@/components/chat/feedback-bar";
import { ProgressSteps, type Step } from "@/components/chat/progress-steps";
import { SourceDialog } from "@/components/chat/source-dialog";
import { LogoMark } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { NOT_FOUND, volumeLabel, type Answer, type Rating, type Source } from "@/lib/qa";
import { cn } from "@/lib/utils";

export type Turn = {
  id: string;
  question: string;
  maxVolume: number | null;
  /** waiting: loaded from history while it is still being answered (in another tab or earlier visit) */
  status: "pending" | "waiting" | "done" | "error";
  steps: Step[];
  startedAt: number;
  seconds: number;
  answer?: Answer;
  error?: string;
  /** The stored rating, for turns loaded from history */
  feedback?: { rating: Rating; comment: string | null } | null;
};

export function ChatTurn({ turn, onRetry }: { turn: Turn; onRetry?: () => void }) {
  const [openSource, setOpenSource] = useState<Source | null>(null);
  const [showAll, setShowAll] = useState(false);
  const answer = turn.answer;

  const refs = useMemo(() => new Set(answer?.sources.map((s) => s.ref) ?? []), [answer]);
  const cited = answer?.sources.filter((s) => s.cited) ?? [];
  const listed = showAll ? (answer?.sources ?? []) : cited;
  const notFound = !!answer && !answer.found;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-muted px-4 py-2.5 text-sm whitespace-pre-wrap">
          {turn.question}
        </div>
      </div>
      {answer?.standaloneQuestion && (
        <p className="-mt-2 text-right text-xs text-muted-foreground">
          Hiểu là: “{answer.standaloneQuestion}”
        </p>
      )}

      <div className="flex gap-3">
        <LogoMark className="mt-0.5 size-6 shrink-0" />
        <div className="min-w-0 flex-1 space-y-3 text-sm">
          {turn.maxVolume !== null && (
            <p className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <EyeOff className="size-3.5" />
              Chỉ tra trong Tập 1–{turn.maxVolume}
            </p>
          )}

          <ProgressSteps steps={turn.steps} pending={turn.status === "pending"} seconds={turn.seconds} />

          {turn.status === "waiting" && (
            <p className="flex items-center gap-2 text-muted-foreground" aria-live="polite">
              <Loader className="size-4 animate-spin" />
              Câu trả lời đang được chuẩn bị…
            </p>
          )}

          {turn.status === "error" && (
            <div className="space-y-2">
              <p className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-destructive">
                <CircleAlert className="mt-0.5 size-4 shrink-0" />
                {turn.error}
              </p>
              {onRetry && (
                <Button variant="outline" size="sm" onClick={onRetry}>
                  <RotateCw />
                  Hỏi lại
                </Button>
              )}
            </div>
          )}

          {answer &&
            (notFound ? (
              <p className="text-muted-foreground">
                Không tìm thấy thông tin này trong các đoạn truyện đã tra
                {turn.maxVolume !== null ? ` (trong phạm vi Tập 1–${turn.maxVolume})` : ""}.
                {answer.answer.trim() !== NOT_FOUND && (
                  <span className="mt-2 block">{answer.answer.replace(NOT_FOUND, "").trim()}</span>
                )}
              </p>
            ) : (
              <AnswerBody
                text={answer.answer}
                refs={refs}
                onCite={(ref) => setOpenSource(answer.sources.find((s) => s.ref === ref) ?? null)}
              />
            ))}

          {answer && answer.sources.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">
                  {showAll
                    ? `Đã đọc ${answer.sources.length} đoạn`
                    : cited.length
                      ? `Nguồn (${cited.length})`
                      : "Không có đoạn nào được trích"}
                </p>
                {answer.sources.length > cited.length && (
                  <button
                    type="button"
                    onClick={() => setShowAll((v) => !v)}
                    className="text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                  >
                    {showAll ? "Chỉ nguồn được trích" : `Xem cả ${answer.sources.length} đoạn đã đọc`}
                  </button>
                )}
              </div>
              <ul className="grid gap-1.5">
                {listed.map((s) => (
                  <li key={s.ref}>
                    <button
                      type="button"
                      onClick={() => setOpenSource(s)}
                      className={cn(
                        "w-full rounded-lg border px-3 py-2 text-left transition-colors hover:bg-muted",
                        !s.cited && "border-dashed",
                      )}
                    >
                      <span className="flex items-baseline gap-2 text-xs">
                        <span className="font-medium text-muted-foreground">[{s.ref}]</span>
                        <span className="font-medium">{volumeLabel(s.volumeKind, s.volumeNumber)}</span>
                        <span className="truncate text-muted-foreground">{s.chapter}</span>
                      </span>
                      <span className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{s.excerpt}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {answer && (
            <FeedbackBar
              messageId={answer.messageId}
              initialRating={turn.feedback?.rating ?? null}
              initialComment={turn.feedback?.comment ?? null}
            />
          )}
        </div>
      </div>

      <SourceDialog source={openSource} onOpenChange={(open) => !open && setOpenSource(null)} />
    </div>
  );
}
