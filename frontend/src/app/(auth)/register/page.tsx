import type { Metadata } from "next";

import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: "Đăng ký · Beako AI" };

export default function RegisterPage() {
  return <RegisterForm />;
}
