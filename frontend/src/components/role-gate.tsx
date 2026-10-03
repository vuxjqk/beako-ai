"use client";

import { notFound } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import type { UserRole } from "@/lib/auth";

/**
 * Hides a page from roles that can't use it. Shows the regular 404 (not "forbidden")
 * so the page's existence isn't revealed. The API enforces the real permission.
 */
export function RoleGate({ roles, children }: { roles: UserRole[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!roles.includes(user.role)) notFound();
  return children;
}
