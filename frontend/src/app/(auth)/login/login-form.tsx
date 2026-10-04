"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";

import { AuthDivider, AuthHeader } from "@/components/auth-header";
import { FormAlert, type FormAlertVariant } from "@/components/form-alert";
import { GoogleButton } from "@/components/google-button";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";
import { loginSchema, type LoginValues } from "@/lib/validations";

export type LoginNotice = "session-expired" | "password-reset" | "account-deleted";

const NOTICE_CONTENT: Record<LoginNotice, { variant: FormAlertVariant; title: string; text: string }> = {
  "session-expired": {
    variant: "warning",
    title: "Phiên đăng nhập đã hết hạn",
    text: "Vui lòng đăng nhập lại để tiếp tục.",
  },
  "password-reset": {
    variant: "success",
    title: "Đã đặt lại mật khẩu",
    text: "Hãy đăng nhập bằng mật khẩu mới của bạn.",
  },
  "account-deleted": {
    variant: "info",
    title: "Tài khoản đã được xoá",
    text: "Cảm ơn bạn đã sử dụng Beako AI.",
  },
};

type Problem = { variant: FormAlertVariant; title?: string; text: string };

export function LoginForm({ next, notice }: { next: string; notice?: LoginNotice }) {
  const router = useRouter();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [googlePending, setGooglePending] = useState(false);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  const onSignedIn = useCallback(() => {
    setGooglePending(true);
    router.replace(next);
  }, [router, next]);

  const onGoogleError = useCallback((text: string) => setProblem({ variant: "error", text }), []);

  async function onSubmit(values: LoginValues) {
    setProblem(null);
    try {
      await authApi.login(values);
      onSignedIn();
    } catch (error) {
      if (isStatus(error, 403)) {
        setProblem({
          variant: "error",
          title: "Tài khoản đã bị vô hiệu hoá",
          text: "Vui lòng liên hệ quản trị viên để được hỗ trợ.",
        });
      } else if (isStatus(error, 429)) {
        const minutes = Math.max(1, Math.ceil((error.retryAfter ?? 900) / 60));
        setProblem({
          variant: "error",
          title: "Đăng nhập sai quá nhiều lần",
          text: `Tài khoản này tạm bị khoá đăng nhập. Vui lòng thử lại sau ${minutes} phút, hoặc đặt lại mật khẩu.`,
        });
      } else {
        setProblem({
          variant: "error",
          text: errorMessage(error, { 401: "Email hoặc mật khẩu không đúng." }),
        });
      }
    }
  }

  const busy = isSubmitting || googlePending;
  // A login problem replaces the notice the user arrived with
  const alert = problem ?? (notice ? NOTICE_CONTENT[notice] : null);

  return (
    <>
      <AuthHeader title="Đăng nhập" description="Chào mừng bạn quay lại Beako AI." />

      {alert && (
        <FormAlert className="mb-5" variant={alert.variant} title={alert.title}>
          {alert.text}
        </FormAlert>
      )}

      <GoogleButton text="signin_with" onSuccess={onSignedIn} onError={onGoogleError} disabled={busy} />

      <AuthDivider />

      <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
        <FieldGroup className="gap-4">
          <Field data-invalid={!!errors.email}>
            <FieldLabel htmlFor="email">Email</FieldLabel>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="ban@vidu.com"
              aria-invalid={!!errors.email}
              disabled={busy}
              {...form.register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>

          <Field data-invalid={!!errors.password}>
            <div className="flex items-center justify-between">
              <FieldLabel htmlFor="password">Mật khẩu</FieldLabel>
              <Link
                href="/forgot-password"
                className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                Quên mật khẩu?
              </Link>
            </div>
            <PasswordInput
              id="password"
              autoComplete="current-password"
              aria-invalid={!!errors.password}
              disabled={busy}
              {...form.register("password")}
            />
            <FieldError errors={[errors.password]} />
          </Field>

          <Button type="submit" className="mt-1 w-full" disabled={busy}>
            {isSubmitting && <Spinner />}
            {isSubmitting ? "Đang đăng nhập…" : "Đăng nhập"}
          </Button>
        </FieldGroup>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Chưa có tài khoản?{" "}
        <Link href="/register" className="font-medium text-foreground underline-offset-4 hover:underline">
          Đăng ký
        </Link>
      </p>
    </>
  );
}
