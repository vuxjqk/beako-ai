"use client";

import { Fragment, type ReactNode } from "react";

/**
 * Renders the model's answer: paragraphs, "-"/"*" bullet lists, **bold**, and citations such
 * as [3], [2][5] or [2, 5] as small buttons that open the cited passage. Deliberately tiny:
 * the answers only use these few constructs, and nothing is rendered as raw HTML.
 */
export function AnswerBody({ text, onCite, refs }: { text: string; onCite: (ref: number) => void; refs: Set<number> }) {
  const blocks = text.trim().split(/\n\s*\n/);
  return (
    <div className="space-y-3 leading-relaxed">
      {blocks.map((block, i) => {
        const lines = block.split("\n").filter((l) => l.trim());
        const bullets = lines.length > 0 && lines.every((l) => /^\s*([-*•]|\d+\.)\s+/.test(l));
        if (bullets) {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5">
              {lines.map((l, j) => (
                <li key={j}>{inline(l.replace(/^\s*([-*•]|\d+\.)\s+/, ""), onCite, refs)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i}>
            {lines.map((l, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {inline(l, onCite, refs)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

const TOKEN = /(\*\*[^*]+\*\*|\[\d+(?:\s*,\s*\d+)*\])/g;

function inline(line: string, onCite: (ref: number) => void, refs: Set<number>): ReactNode[] {
  return line.split(TOKEN).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    const cite = part.match(/^\[(\d+(?:\s*,\s*\d+)*)\]$/);
    if (cite) {
      return (
        <Fragment key={i}>
          {cite[1].split(/\s*,\s*/).map(Number).map((n) =>
            refs.has(n) ? (
              <button
                key={n}
                type="button"
                onClick={() => onCite(n)}
                className="mx-0.5 inline-flex h-4.5 min-w-4.5 translate-y-[-2px] items-center justify-center rounded bg-muted px-1 align-baseline text-[0.7rem] font-medium text-muted-foreground hover:bg-primary hover:text-primary-foreground"
                aria-label={`Xem nguồn ${n}`}
              >
                {n}
              </button>
            ) : (
              <span key={n} className="text-muted-foreground">[{n}]</span>
            ),
          )}
        </Fragment>
      );
    }
    return part;
  });
}
