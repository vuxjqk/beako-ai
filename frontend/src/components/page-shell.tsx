import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** Standard content column + heading for app pages. */
export function PageShell({
  title,
  description,
  children,
  className,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main className={cn("mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-10", className)}>
      <div className="mb-8 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
    </main>
  );
}

export function EmptyState({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed px-6 py-16 text-center">
      <Icon className="mb-3 size-8 text-muted-foreground" />
      <p className="font-medium">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{text}</p>
    </div>
  );
}
