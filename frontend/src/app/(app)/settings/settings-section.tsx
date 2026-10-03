import { cn } from "@/lib/utils";

export function SettingsSection({
  title,
  description,
  children,
  footer,
  tone = "default",
}: {
  title: string;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  tone?: "default" | "danger";
}) {
  return (
    <section className={cn("rounded-xl border bg-card", tone === "danger" && "border-destructive/30")}>
      <div className="space-y-4 p-5 sm:p-6">
        <div className="space-y-1">
          <h2 className={cn("font-semibold", tone === "danger" && "text-destructive")}>{title}</h2>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
        {children}
      </div>
      {footer && (
        <div className="flex items-center justify-end gap-2 border-t bg-muted/30 px-5 py-3 sm:px-6">{footer}</div>
      )}
    </section>
  );
}
