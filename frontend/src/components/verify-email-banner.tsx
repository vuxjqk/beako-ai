"use client";

import { MailWarning } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";

export function VerifyEmailBanner() {
  const { user } = useAuth();
  const pathname = usePathname();
  if (user.emailVerifiedAt) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b bg-muted/40 px-4 py-2 text-sm">
      <MailWarning className="size-4 shrink-0 text-amber-500" />
      <span className="text-muted-foreground">
        Email <span className="font-medium text-foreground">{user.email}</span> chưa được xác thực.
      </span>
      <Link
        href={`/verify-email?${new URLSearchParams({ next: pathname })}`}
        className="font-medium text-primary underline-offset-4 hover:underline"
      >
        Xác thực ngay
      </Link>
    </div>
  );
}
