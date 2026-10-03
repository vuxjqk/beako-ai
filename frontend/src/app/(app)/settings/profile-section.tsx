"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck, CircleAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { useAuth } from "@/components/auth-provider";
import { FormAlert } from "@/components/form-alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";
import { profileSchema, type ProfileValues } from "@/lib/validations";

import { SettingsSection } from "./settings-section";

export function ProfileSection() {
  const { user, setUser } = useAuth();
  const [problem, setProblem] = useState<string | null>(null);

  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { fullName: user.fullName, email: user.email },
  });
  const { errors, isSubmitting, isDirty } = form.formState;
  const emailValue = useWatch({ control: form.control, name: "email" });
  const emailChanging = emailValue.trim().toLowerCase() !== user.email;

  async function onSubmit(values: ProfileValues) {
    setProblem(null);
    const changes: { fullName?: string; email?: string } = {};
    if (values.fullName !== user.fullName) changes.fullName = values.fullName;
    if (values.email.toLowerCase() !== user.email) changes.email = values.email;

    try {
      const updated = await authApi.updateMe(changes);
      setUser(updated);
      form.reset({ fullName: updated.fullName, email: updated.email });
      toast.success(
        changes.email ? "Đã cập nhật. Hãy xác thực địa chỉ email mới." : "Đã cập nhật thông tin cá nhân",
      );
    } catch (error) {
      if (isStatus(error, 409)) {
        form.setError("email", { message: "Email này đã được tài khoản khác sử dụng." });
      } else {
        setProblem(errorMessage(error));
      }
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
      <SettingsSection
        title="Thông tin cá nhân"
        footer={
          <>
            {isDirty && (
              <Button type="button" variant="ghost" onClick={() => form.reset()} disabled={isSubmitting}>
                Huỷ
              </Button>
            )}
            <Button type="submit" disabled={!isDirty || isSubmitting}>
              {isSubmitting && <Spinner />}
              Lưu thay đổi
            </Button>
          </>
        }
      >
        {problem && <FormAlert variant="error">{problem}</FormAlert>}
        <FieldGroup className="gap-4">
          <Field data-invalid={!!errors.fullName}>
            <FieldLabel htmlFor="fullName">Họ và tên</FieldLabel>
            <Input
              id="fullName"
              autoComplete="name"
              aria-invalid={!!errors.fullName}
              disabled={isSubmitting}
              {...form.register("fullName")}
            />
            <FieldError errors={[errors.fullName]} />
          </Field>

          <Field data-invalid={!!errors.email}>
            <div className="flex flex-wrap items-center gap-2">
              <FieldLabel htmlFor="email">Email</FieldLabel>
              {user.emailVerifiedAt ? (
                <Badge variant="secondary" className="gap-1">
                  <BadgeCheck className="size-3 text-emerald-500" />
                  Đã xác thực
                </Badge>
              ) : (
                <Badge variant="secondary" className="gap-1">
                  <CircleAlert className="size-3 text-amber-500" />
                  Chưa xác thực
                </Badge>
              )}
              {user.googleLinked && <Badge variant="outline">Đã liên kết Google</Badge>}
              {!user.emailVerifiedAt && !emailChanging && (
                <Link
                  href="/verify-email?next=/settings"
                  className="ml-auto text-sm font-medium text-primary underline-offset-4 hover:underline"
                >
                  Xác thực ngay
                </Link>
              )}
            </div>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={!!errors.email}
              disabled={isSubmitting}
              {...form.register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>

          {emailChanging && !errors.email && (
            <FormAlert variant="warning">
              Sau khi đổi, bạn cần xác thực lại địa chỉ email mới
              {user.googleLinked && " và liên kết đăng nhập Google hiện tại sẽ bị huỷ"}.
            </FormAlert>
          )}
        </FieldGroup>
      </SettingsSection>
    </form>
  );
}
