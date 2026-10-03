import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

const VARIANTS = {
  error: { icon: CircleAlert, className: "border-destructive/30 text-destructive" },
  warning: { icon: TriangleAlert, className: "[&>svg]:text-amber-500" },
  success: { icon: CircleCheck, className: "[&>svg]:text-emerald-500" },
  info: { icon: Info, className: "[&>svg]:text-primary" },
} as const;

export type FormAlertVariant = keyof typeof VARIANTS;

/** Inline status message above/inside forms (errors, notices, confirmations). */
export function FormAlert({
  variant = "error",
  title,
  children,
  className,
}: {
  variant?: FormAlertVariant;
  title?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const { icon: Icon, className: variantClass } = VARIANTS[variant];
  return (
    <Alert
      variant={variant === "error" ? "destructive" : "default"}
      className={cn(variantClass, className)}
    >
      <Icon />
      {title && <AlertTitle>{title}</AlertTitle>}
      {children && <AlertDescription>{children}</AlertDescription>}
    </Alert>
  );
}
