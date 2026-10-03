import { BookOpen } from "lucide-react";

import { cn } from "@/lib/utils";

export const SLOGAN = "Bách khoa toàn thư";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground",
        className,
      )}
    >
      <BookOpen className="size-[55%]" strokeWidth={2.25} />
    </span>
  );
}

export function Logo({ withSlogan = false }: { withSlogan?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="flex flex-col leading-tight">
        <span className="font-semibold tracking-tight">Beako AI</span>
        {withSlogan && <span className="text-xs text-muted-foreground">{SLOGAN}</span>}
      </span>
    </span>
  );
}
