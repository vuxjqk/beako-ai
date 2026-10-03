import type { Metadata } from "next";

import { ForgotPasswordForm } from "./forgot-password-form";

export const metadata: Metadata = { title: "Quên mật khẩu · Beako AI" };

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
