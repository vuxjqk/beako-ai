"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { FormAlert } from "@/components/form-alert";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { adminUsersApi, type ManagedRole } from "@/lib/admin";
import { ROLE_LABELS, type User } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";
import {
  adminCreateUserSchema,
  adminUpdateUserSchema,
  type AdminUpdateUserValues,
} from "@/lib/validations";

const MANAGED_ROLES: ManagedRole[] = ["user", "expert"];

/**
 * Create a new account (`user` omitted) or edit an existing one.
 * Give it a fresh `key` each time it opens so the form starts from the target's current values.
 */
export function UserFormDialog({
  open,
  onOpenChange,
  user,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User;
  onSaved: (user: User, created: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);

  return (
    <Dialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <DialogContent className="sm:max-w-md" showCloseButton={!busy}>
        <DialogHeader>
          <DialogTitle>{user ? "Chỉnh sửa tài khoản" : "Tạo tài khoản"}</DialogTitle>
          <DialogDescription>
            {user
              ? "Chỉ những trường bạn thay đổi mới được cập nhật."
              : "Tài khoản mới được xác thực email sẵn và có thể đăng nhập ngay."}
          </DialogDescription>
        </DialogHeader>
        <UserForm
          user={user}
          onBusyChange={setBusy}
          onCancel={() => onOpenChange(false)}
          onSaved={onSaved}
        />
      </DialogContent>
    </Dialog>
  );
}

function UserForm({
  user,
  onBusyChange,
  onCancel,
  onSaved,
}: {
  user?: User;
  onBusyChange: (busy: boolean) => void;
  onCancel: () => void;
  onSaved: (user: User, created: boolean) => void;
}) {
  const editing = !!user;
  const [problem, setProblem] = useState<string | null>(null);

  const form = useForm<AdminUpdateUserValues>({
    resolver: zodResolver(editing ? adminUpdateUserSchema : adminCreateUserSchema),
    defaultValues: {
      fullName: user?.fullName ?? "",
      email: user?.email ?? "",
      password: "",
      // Admins never show up in the list, but keep the type honest
      role: user?.role === "expert" ? "expert" : "user",
    },
  });
  const { errors, isSubmitting, isDirty } = form.formState;
  const [emailValue, passwordValue] = useWatch({ control: form.control, name: ["email", "password"] });
  const emailChanging = editing && emailValue.trim().toLowerCase() !== user.email;
  const passwordChanging = editing && passwordValue !== "";

  async function onSubmit(values: AdminUpdateUserValues) {
    setProblem(null);
    onBusyChange(true);
    try {
      let saved: User;
      if (user) {
        const changes: { fullName?: string; email?: string; password?: string; role?: ManagedRole } = {};
        if (values.fullName !== user.fullName) changes.fullName = values.fullName;
        if (values.email.toLowerCase() !== user.email) changes.email = values.email;
        if (values.password) changes.password = values.password;
        if (values.role !== user.role) changes.role = values.role;
        saved = await adminUsersApi.update(user.id, changes);
        toast.success(`Đã cập nhật tài khoản ${saved.fullName}`);
      } else {
        saved = await adminUsersApi.create(values);
        toast.success(`Đã tạo tài khoản ${saved.fullName}`);
      }
      onSaved(saved, !editing);
    } catch (error) {
      if (isStatus(error, 409)) {
        form.setError("email", { message: "Email này đã được tài khoản khác sử dụng." });
      } else {
        setProblem(
          errorMessage(error, { 404: "Tài khoản không còn tồn tại. Hãy tải lại danh sách." }),
        );
      }
    } finally {
      onBusyChange(false);
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="grid gap-4">
      {problem && <FormAlert variant="error">{problem}</FormAlert>}
      <FieldGroup className="gap-4">
        <Field data-invalid={!!errors.fullName}>
          <FieldLabel htmlFor="admin-fullName">Họ và tên</FieldLabel>
          <Input
            id="admin-fullName"
            autoComplete="off"
            aria-invalid={!!errors.fullName}
            disabled={isSubmitting}
            {...form.register("fullName")}
          />
          <FieldError errors={[errors.fullName]} />
        </Field>

        <Field data-invalid={!!errors.email}>
          <FieldLabel htmlFor="admin-email">Email</FieldLabel>
          <Input
            id="admin-email"
            type="email"
            autoComplete="off"
            aria-invalid={!!errors.email}
            disabled={isSubmitting}
            {...form.register("email")}
          />
          <FieldError errors={[errors.email]} />
        </Field>

        <Field data-invalid={!!errors.role}>
          <FieldLabel htmlFor="admin-role">Vai trò</FieldLabel>
          <Controller
            control={form.control}
            name="role"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange} disabled={isSubmitting}>
                <SelectTrigger id="admin-role" className="w-full" onBlur={field.onBlur}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MANAGED_ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {ROLE_LABELS[role]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          <FieldError errors={[errors.role]} />
        </Field>

        <Field data-invalid={!!errors.password}>
          <FieldLabel htmlFor="admin-password">{editing ? "Đặt lại mật khẩu" : "Mật khẩu"}</FieldLabel>
          <PasswordInput
            id="admin-password"
            autoComplete="new-password"
            placeholder={editing ? "Để trống nếu không đổi" : undefined}
            aria-invalid={!!errors.password}
            disabled={isSubmitting}
            {...form.register("password")}
          />
          {errors.password ? (
            <FieldError errors={[errors.password]} />
          ) : (
            <FieldDescription>Ít nhất 8 ký tự.</FieldDescription>
          )}
        </Field>

        {(emailChanging || passwordChanging) && (
          <FormAlert variant="warning">
            {emailChanging &&
              `Mã OTP đã gửi tới email cũ sẽ hết hiệu lực${user.googleLinked ? " và liên kết Google sẽ bị huỷ" : ""}. `}
            {passwordChanging && "Người dùng sẽ bị đăng xuất khỏi mọi thiết bị."}
          </FormAlert>
        )}
      </FieldGroup>

      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Huỷ
        </Button>
        <Button type="submit" disabled={(editing && !isDirty) || isSubmitting}>
          {isSubmitting && <Spinner />}
          {editing ? "Lưu thay đổi" : "Tạo tài khoản"}
        </Button>
      </DialogFooter>
    </form>
  );
}
