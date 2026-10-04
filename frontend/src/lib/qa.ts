import { api, ApiError, apiStream } from "@/lib/api";

/** Main volumes in the corpus; the spoiler limit is one of these. */
export const MAX_VOLUME = 28;

export type Source = {
  ref: number;
  cited: boolean;
  volume: string;
  volumeKind: "main" | "short_story_collection";
  volumeNumber: number;
  chapter: string;
  paragraphs: [number, number];
  chunkId: number;
  citation: string;
  excerpt: string;
};

export type Answer = {
  question: string;
  answer: string;
  found: boolean;
  sources: Source[];
  mode: string;
  maxVolume: number | null;
  conversationId: string;
  messageId: string;
  timingsMs: { retrieval?: number; llm?: number };
};

/** Progress reported while the answer is prepared (see POST /qa/stream). */
export type StatusEvent =
  | { type: "route"; mode: "simple" | "agent"; reason: string | null }
  | { type: "llm"; step: number; final: boolean }
  | { type: "tool"; step: number; tool: string; args: Record<string, unknown>; new_passages?: number };

export type Passage = {
  chunkId: number;
  citation: string;
  volume: string;
  chapter: string;
  paragraphs: [number, number];
  text: string;
};

export type Rating = 1 | -1;

/** "Volume 7" -> "Tập 7", "Short Story Collection 2" -> "Tuyển tập truyện ngắn 2". */
export function volumeLabel(kind: Source["volumeKind"], number: number): string {
  return kind === "main" ? `Tập ${number}` : `Tuyển tập truyện ngắn ${number}`;
}

/** The backend's English "not found" sentence (agent and simple path use the same one). */
export const NOT_FOUND = "Not found in the provided passages.";

type Handlers = {
  onStart?: (data: { conversationId: string }) => void;
  onStatus: (event: StatusEvent) => void;
};

/**
 * Ask a question and follow its progress. Resolves with the stored answer; rejects with an
 * ApiError when the backend reports a failure (before or during the stream).
 */
export async function askStream(
  body: { question: string; maxVolume: number | null; conversationId: string | null },
  handlers: Handlers,
  signal?: AbortSignal,
): Promise<Answer> {
  const res = await apiStream("/qa/stream", body, signal);
  if (!res.body) throw new ApiError(500, "Empty response");
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    // Events are separated by a blank line; keep any incomplete tail for the next chunk
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      let event = "message";
      const data: string[] = [];
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith(":")) continue; // comment: padding or keep-alive
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (!data.length) continue;
      const payload = JSON.parse(data.join("\n"));
      if (event === "start") handlers.onStart?.(payload);
      else if (event === "status") handlers.onStatus(payload as StatusEvent);
      else if (event === "answer") return payload as Answer;
      else if (event === "error") throw new ApiError(payload.status ?? 500, payload.detail ?? "Error");
    }
  }
  throw new ApiError(502, "The answer stream ended unexpectedly");
}

export const qaApi = {
  feedback: (messageId: string, rating: Rating | null, comment?: string) =>
    api<{ rating: Rating | null; comment: string | null }>(`/qa/messages/${messageId}/feedback`, {
      method: "PUT",
      json: { rating, comment: comment?.trim() || null },
    }),
  passage: (chunkId: number) => api<Passage>(`/qa/chunks/${chunkId}`),
};
