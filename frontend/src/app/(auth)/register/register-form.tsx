"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";

import { AuthDivider, AuthHeader } from "@/components/auth-header";
import { FormAlert } from "@/components/form-alert";
import { GoogleButton } from "@/components/google-button";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";
import { registerSchema, type RegisterValues } from "@/lib/validations";

export function RegisterForm() {
  const router = useRouter();
  const [problem, setProblem] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { fullName: "", email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  const onGoogleSuccess = useCallback(() => {
    setRedirecting(true);
    router.replace("/");
  }, [router]);
  const onGoogleError = useCallback((text: string) => setProblem(text), []);

  async function onSubmit(values: RegisterValues) {
    setProblem(null);
    try {
      await authApi.register(values);
    } catch (error) {
      if (isStatus(error, 409)) {
        form.setError("email", { type: "taken", message: "Email này đã được sử dụng." }, { shouldFocus: true });
      } else {
        setProblem(errorMessage(error));
      }
      return;
    }

    setRedirecting(true);
    // Registration already signed the user in; mail the verification code right away.
    // If that fails the verify page offers to send it again.
    const sent = await authApi.sendVerification().then(
      () => true,
      () => false,
    );
    router.replace(sent ? "/verify-email?sent=1" : "/verify-email");
  }

  const busy = isSubmitting || redirecting;

  return (
    <>
      <AuthHeader title="Tạo tài khoản" description="Bắt đầu khám phá bách khoa toàn thư cùng AI." />

      {problem && (
        <FormAlert className="mb-5" variant="error">
          {problem}
        </FormAlert>
      )}

      <GoogleButton text="signup_with" onSuccess={onGoogleSuccess} onError={onGoogleError} disabled={busy} />

      <AuthDivider />

      <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
        <FieldGroup className="gap-4">
          <Field data-invalid={!!errors.fullName}>
            <FieldLabel htmlFor="fullName">Họ và tên</FieldLabel>
            <Input
              id="fullName"
              autoComplete="name"
              placeholder="Nguyễn Văn A"
              aria-invalid={!!errors.fullName}
              disabled={busy}
              {...form.register("fullName")}
            />
            <FieldError errors={[errors.fullName]} />
          </Field>

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
            {errors.email?.type === "taken" ? (
              <FieldError>
                Email này đã được sử dụng.{" "}
                <Link href="/login" className="underline underline-offset-4">
                  Đăng nhập?
                </Link>
              </FieldError>
            ) : (
              <FieldError errors={[errors.email]} />
            )}
          </Field>

          <Field data-invalid={!!errors.password}>
            <FieldLabel htmlFor="password">Mật khẩu</FieldLabel>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              disabled={busy}
              {...form.register("password")}
            />
            {errors.password ? (
              <FieldError errors={[errors.password]} />
            ) : (
              <FieldDescription>Tối thiểu 8 ký tự.</FieldDescription>
            )}
          </Field>

          <Button type="submit" className="mt-1 w-full" disabled={busy}>
            {busy && <Spinner />}
            {busy ? "Đang tạo tài khoản…" : "Tạo tài khoản"}
          </Button>
        </FieldGroup>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Đã có tài khoản?{" "}
        <Link href="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
          Đăng nhập
        </Link>
      </p>
    </>
  );
}
