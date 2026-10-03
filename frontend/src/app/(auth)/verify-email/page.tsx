import type { Metadata } from "next";

import { safeNext } from "@/lib/auth";

import { VerifyEmailForm } from "./verify-email-form";

export const metadata: Metadata = { title: "Xác thực email · Beako AI" };

// Not a public page: proxy.ts requires a session, since the verify endpoints need one.
export default async function VerifyEmailPage({ searchParams }: PageProps<"/verify-email">) {
  const params = await searchParams;
  return <VerifyEmailForm alreadySent={params.sent === "1"} next={safeNext(params.next)} />;
}
