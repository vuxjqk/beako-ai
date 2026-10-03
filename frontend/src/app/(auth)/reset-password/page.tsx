import type { Metadata } from "next";

import { ResetPasswordForm } from "./reset-password-form";

export const metadata: Metadata = { title: "Đặt lại mật khẩu · Beako AI" };

export default async function ResetPasswordPage({ searchParams }: PageProps<"/reset-password">) {
  const params = await searchParams;
  const email = typeof params.email === "string" ? params.email : "";
  return <ResetPasswordForm initialEmail={email} justSent={params.sent === "1"} />;
}
