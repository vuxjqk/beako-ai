"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { useAuth } from "@/components/auth-provider";
import { FormAlert } from "@/components/form-alert";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";
import { changePasswordSchema, type ChangePasswordValues } from "@/lib/validations";

import { SettingsSection } from "./settings-section";

export function PasswordSection() {
  const { user } = useAuth();
  return user.hasPassword ? <ChangePasswordForm /> : <SetPasswordByEmail email={user.email} />;
}

function ChangePasswordForm() {
  const [problem, setProblem] = useState<string | null>(null);
  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
  });
  const { errors, isSubmitting, isDirty } = form.formState;

  async function onSubmit(values: ChangePasswordValues) {
    setProblem(null);
    try {
      await authApi.changePassword(values);
      form.reset();
      toast.success("Đã đổi mật khẩu", {
        description: "Các thiết bị khác đã được đăng xuất.",
      });
    } catch (error) {
      if (isStatus(error, 400) && error.detail.startsWith("Current password")) {
        form.setError("currentPassword", { message: "Mật khẩu hiện tại không đúng." }, { shouldFocus: true });
      } else {
        setProblem(errorMessage(error, { 400: "Không thể đổi mật khẩu. Vui lòng kiểm tra lại." }));
      }
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
      <SettingsSection
        title="Mật khẩu"
        description="Sau khi đổi mật khẩu, các thiết bị khác sẽ bị đăng xuất."
        footer={
          <Button type="submit" disabled={!isDirty || isSubmitting}>
            {isSubmitting && <Spinner />}
            Đổi mật khẩu
          </Button>
        }
      >
        {problem && <FormAlert variant="error">{problem}</FormAlert>}
        <FieldGroup className="gap-4">
          <Field data-invalid={!!errors.currentPassword}>
            <FieldLabel htmlFor="currentPassword">Mật khẩu hiện tại</FieldLabel>
            <PasswordInput
              id="currentPassword"
              autoComplete="current-password"
              aria-invalid={!!errors.currentPassword}
              disabled={isSubmitting}
              {...form.register("currentPassword")}
            />
            <FieldError errors={[errors.currentPassword]} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field data-invalid={!!errors.newPassword}>
              <FieldLabel htmlFor="newPassword">Mật khẩu mới</FieldLabel>
              <PasswordInput
                id="newPassword"
                autoComplete="new-password"
                aria-invalid={!!errors.newPassword}
                disabled={isSubmitting}
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
                disabled={isSubmitting}
                {...form.register("confirmPassword")}
              />
              <FieldError errors={[errors.confirmPassword]} />
            </Field>
          </div>
        </FieldGroup>
      </SettingsSection>
    </form>
  );
}

/** Google-only accounts have no password; they set one through the reset-by-email flow. */
function SetPasswordByEmail({ email }: { email: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function start() {
    setProblem(null);
    setPending(true);
    try {
      await authApi.forgotPassword(email);
      router.push(`/reset-password?${new URLSearchParams({ email, sent: "1" })}`);
    } catch (error) {
      setProblem(errorMessage(error));
      setPending(false);
    }
  }

  return (
    <SettingsSection
      title="Mật khẩu"
      description="Tài khoản của bạn đang đăng nhập bằng Google và chưa có mật khẩu."
      footer={
        <Button variant="outline" onClick={start} disabled={pending}>
          {pending && <Spinner />}
          Thiết lập mật khẩu qua email
        </Button>
      }
    >
      {problem && <FormAlert variant="error">{problem}</FormAlert>}
      <p className="text-sm text-muted-foreground">
        Chúng tôi sẽ gửi mã tới <span className="font-medium text-foreground">{email}</span> để bạn đặt mật
        khẩu. Sau khi đặt xong, bạn cần đăng nhập lại.
      </p>
    </SettingsSection>
  );
}
