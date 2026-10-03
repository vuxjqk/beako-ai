"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthHeader } from "@/components/auth-header";
import { FormAlert } from "@/components/form-alert";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";
import { forgotPasswordSchema, type ForgotPasswordValues } from "@/lib/validations";

export function ForgotPasswordForm() {
  const router = useRouter();
  const [problem, setProblem] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  const form = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit({ email }: ForgotPasswordValues) {
    setProblem(null);
    try {
      // The backend answers the same way whether or not the email exists
      await authApi.forgotPassword(email);
    } catch (error) {
      setProblem(errorMessage(error));
      return;
    }
    setRedirecting(true);
    router.push(`/reset-password?${new URLSearchParams({ email, sent: "1" })}`);
  }

  const busy = isSubmitting || redirecting;

  return (
    <>
      <AuthHeader
        title="Quên mật khẩu"
        description="Nhập email tài khoản của bạn, chúng tôi sẽ gửi mã để đặt lại mật khẩu."
      />

      {problem && (
        <FormAlert className="mb-5" variant="error">
          {problem}
        </FormAlert>
      )}

      <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
        <FieldGroup className="gap-4">
          <Field data-invalid={!!errors.email}>
            <FieldLabel htmlFor="email">Email</FieldLabel>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="ban@vidu.com"
              autoFocus
              aria-invalid={!!errors.email}
              disabled={busy}
              {...form.register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy && <Spinner />}
            {busy ? "Đang gửi…" : "Gửi mã đặt lại"}
          </Button>
        </FieldGroup>
      </form>

      <p className="mt-6 text-center text-sm">
        <Link
          href="/login"
          className="inline-flex items-center gap-1 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Quay lại đăng nhập
        </Link>
      </p>
    </>
  );
}
