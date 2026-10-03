"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthHeader } from "@/components/auth-header";
import { FormAlert } from "@/components/form-alert";
import { OtpInput } from "@/components/otp-input";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useCountdown } from "@/hooks/use-countdown";
import { authApi } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";
import { emailSchema, resetPasswordSchema, type ResetPasswordValues } from "@/lib/validations";

const RESEND_COOLDOWN = 60;

export function ResetPasswordForm({ initialEmail, justSent }: { initialEmail: string; justSent: boolean }) {
  const router = useRouter();
  const [problem, setProblem] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [done, setDone] = useState(false);
  const cooldown = useCountdown(justSent ? RESEND_COOLDOWN : 0);

  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { email: initialEmail, otp: "", newPassword: "", confirmPassword: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function resend() {
    const email = emailSchema.safeParse(form.getValues("email"));
    if (!email.success) {
      form.setError("email", { message: email.error.issues[0].message }, { shouldFocus: true });
      return;
    }
    setProblem(null);
    setResending(true);
    try {
      await authApi.forgotPassword(email.data);
      cooldown.start(RESEND_COOLDOWN);
      toast.success("Nếu email đã đăng ký, mã mới đã được gửi");
    } catch (error) {
      setProblem(errorMessage(error));
    } finally {
      setResending(false);
    }
  }

  async function onSubmit(values: ResetPasswordValues) {
    setProblem(null);
    try {
      await authApi.resetPassword(values);
    } catch (error) {
      if (isStatus(error, 400)) {
        form.setError("otp", { message: "Mã không đúng hoặc đã hết hạn." });
        form.setValue("otp", "");
      } else {
        setProblem(errorMessage(error));
      }
      return;
    }
    setDone(true);
    router.replace("/login?reason=password-reset");
  }

  const busy = isSubmitting || done;

  return (
    <>
      <AuthHeader
        title="Đặt lại mật khẩu"
        description="Nhập mã 6 số trong email và mật khẩu mới của bạn."
      />

      {justSent && !problem && (
        <FormAlert className="mb-5" variant="info">
          Nếu email đã được đăng ký, mã đặt lại mật khẩu sẽ được gửi trong giây lát. Hãy kiểm tra cả
          thư mục spam.
        </FormAlert>
      )}
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
              aria-invalid={!!errors.email}
              disabled={busy}
              {...form.register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>

          <Field data-invalid={!!errors.otp}>
            <div className="flex items-center justify-between">
              <FieldLabel htmlFor="otp">Mã xác nhận</FieldLabel>
              {cooldown.active ? (
                <span className="text-sm text-muted-foreground">Gửi lại sau {cooldown.seconds}s</span>
              ) : (
                <button
                  type="button"
                  onClick={resend}
                  disabled={resending || busy}
                  className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline disabled:opacity-50"
                >
                  {resending ? "Đang gửi…" : justSent ? "Gửi lại mã" : "Gửi mã"}
                </button>
              )}
            </div>
            <Controller
              control={form.control}
              name="otp"
              render={({ field }) => (
                <OtpInput
                  id="otp"
                  value={field.value}
                  onChange={field.onChange}
                  disabled={busy}
                  invalid={!!errors.otp}
                  autoFocus={!!initialEmail}
                />
              )}
            />
            <FieldError errors={[errors.otp]} />
          </Field>

          <Field data-invalid={!!errors.newPassword}>
            <FieldLabel htmlFor="newPassword">Mật khẩu mới</FieldLabel>
            <PasswordInput
              id="newPassword"
              autoComplete="new-password"
              aria-invalid={!!errors.newPassword}
              disabled={busy}
              {...form.register("newPassword")}
            />
            {errors.newPassword ? (
              <FieldError errors={[errors.newPassword]} />
            ) : (
              <FieldDescription>Tối thiểu 8 ký tự.</FieldDescription>
            )}
          </Field>

          <Field data-invalid={!!errors.confirmPassword}>
            <FieldLabel htmlFor="confirmPassword">Xác nhận mật khẩu mới</FieldLabel>
            <PasswordInput
              id="confirmPassword"
              autoComplete="new-password"
              aria-invalid={!!errors.confirmPassword}
              disabled={busy}
              {...form.register("confirmPassword")}
            />
            <FieldError errors={[errors.confirmPassword]} />
          </Field>

          <Button type="submit" className="mt-1 w-full" disabled={busy}>
            {busy && <Spinner />}
            {busy ? "Đang đặt lại…" : "Đặt lại mật khẩu"}
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
