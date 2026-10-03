import type { Metadata } from "next";

import { safeNext } from "@/lib/auth";

import { LoginForm, type LoginNotice } from "./login-form";

export const metadata: Metadata = { title: "Đăng nhập · Beako AI" };

const NOTICES = ["session-expired", "password-reset", "account-deleted"] as const;

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const params = await searchParams;
  const reason = typeof params.reason === "string" ? params.reason : undefined;
  const notice = NOTICES.find((n) => n === reason) as LoginNotice | undefined;
  return <LoginForm next={safeNext(params.next)} notice={notice} />;
}
