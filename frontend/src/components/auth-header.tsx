export function AuthHeader({ title, description }: { title: string; description?: React.ReactNode }) {
  return (
    <div className="mb-6 space-y-1.5">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}

export function AuthDivider({ label = "hoặc" }: { label?: string }) {
  return (
    <div className="my-5 flex items-center gap-3 text-xs uppercase text-muted-foreground">
      <span className="h-px flex-1 bg-border" />
      {label}
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}
