"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/lib/errors";
import { qaApi, type Rating } from "@/lib/qa";
import { cn } from "@/lib/utils";

/**
 * "Is this answer right?" Ratings are stored with the answer and become evaluation data.
 * Clicking the chosen rating again takes it back; a "wrong" rating can carry a comment.
 */
export function FeedbackBar({ messageId }: { messageId: string }) {
  const [rating, setRating] = useState<Rating | null>(null);
  const [comment, setComment] = useState("");
  const [commentSent, setCommentSent] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save(next: Rating | null, withComment?: string) {
    setSaving(true);
    try {
      await qaApi.feedback(messageId, next, withComment);
      setRating(next);
      if (withComment !== undefined) {
        setCommentSent(true);
        toast.success("Cảm ơn bạn đã góp ý");
      } else if (next !== null) {
        setCommentSent(false);
        toast.success("Đã ghi nhận phản hồi");
      }
    } catch (error) {
      toast.error(errorMessage(error, { 404: "Không tìm thấy câu trả lời này." }));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <span className="mr-1">Câu trả lời này đúng không?</span>
        <Button
          variant="ghost"
          size="icon-sm"
          disabled={saving}
          onClick={() => save(rating === 1 ? null : 1)}
          aria-pressed={rating === 1}
          aria-label="Đúng"
          className={cn(rating === 1 && "bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary")}
        >
          <ThumbsUp />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          disabled={saving}
          onClick={() => save(rating === -1 ? null : -1)}
          aria-pressed={rating === -1}
          aria-label="Sai"
          className={cn(rating === -1 && "bg-destructive/10 text-destructive hover:bg-destructive/15 hover:text-destructive")}
        >
          <ThumbsDown />
        </Button>
        {saving && <Spinner className="size-3.5" />}
      </div>

      {rating === -1 && !commentSent && (
        <form
          className="flex flex-col gap-2 sm:flex-row sm:items-start"
          onSubmit={(e) => {
            e.preventDefault();
            if (comment.trim()) save(-1, comment);
          }}
        >
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            maxLength={2000}
            placeholder="Sai ở đâu? Đáp án đúng là gì? (không bắt buộc)"
            className="w-full flex-1 resize-none rounded-lg border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          <Button type="submit" size="sm" variant="outline" disabled={saving || !comment.trim()}>
            Gửi góp ý
          </Button>
        </form>
      )}
    </div>
  );
}
