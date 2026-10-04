"use client";

import { useEffect, useState } from "react";

import { FormAlert } from "@/components/form-alert";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { errorMessage } from "@/lib/errors";
import { qaApi, volumeLabel, type Passage, type Source } from "@/lib/qa";

/** Full text of a cited passage, loaded when opened. */
export function SourceDialog({ source, onOpenChange }: { source: Source | null; onOpenChange: (open: boolean) => void }) {
  // The last load, tagged with its chunk so a stale result is never shown for another source
  const [loaded, setLoaded] = useState<{ chunkId: number; passage?: Passage; problem?: string } | null>(null);
  // Keep the last source while the close animation plays
  const [shown, setShown] = useState(source);
  if (source && source !== shown) setShown(source);
  const current = loaded && shown && loaded.chunkId === shown.chunkId ? loaded : null;
  const passage = current?.passage ?? null;
  const problem = current?.problem ?? null;

  useEffect(() => {
    if (!source) return;
    let cancelled = false;
    const chunkId = source.chunkId;
    qaApi
      .passage(chunkId)
      .then((p) => !cancelled && setLoaded({ chunkId, passage: p }))
      .catch(
        (error) =>
          !cancelled && setLoaded({ chunkId, problem: errorMessage(error, { 404: "Không tìm thấy đoạn trích này." }) }),
      );
    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <Dialog open={!!source} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            [{shown?.ref}] {shown && volumeLabel(shown.volumeKind, shown.volumeNumber)}
          </DialogTitle>
          <DialogDescription>
            {shown?.chapter}
            {shown && ` · đoạn ${shown.paragraphs[0]}–${shown.paragraphs[1]}`}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto pr-1 text-sm leading-relaxed">
          {problem ? (
            <FormAlert variant="error">{problem}</FormAlert>
          ) : passage ? (
            <p className="whitespace-pre-line">{passage.text}</p>
          ) : (
            <div className="space-y-2">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          )}
        </div>
        <p className="text-xs text-muted-foreground">Nguyên văn bản tiếng Anh của light novel.</p>
      </DialogContent>
    </Dialog>
  );
}
