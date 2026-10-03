import { z } from "zod";

// Mirrors the backend rules (src/schemas/auth.py) so most errors are caught before a request.

export const emailSchema = z
  .string()
  .trim()
  .min(1, "Vui lòng nhập email")
  .pipe(z.email("Email không hợp lệ"));

export const fullNameSchema = z
  .string()
  .trim()
  .min(1, "Vui lòng nhập họ tên")
  .max(255, "Họ tên tối đa 255 ký tự");

export const newPasswordSchema = z
  .string()
  .min(8, "Mật khẩu cần ít nhất 8 ký tự")
  // bcrypt only uses the first 72 bytes
  .refine((value) => new TextEncoder().encode(value).length <= 72, "Mật khẩu quá dài");

export const otpSchema = z.string().regex(/^\d{6}$/, "Mã gồm 6 chữ số");

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Vui lòng nhập mật khẩu"),
});

export const registerSchema = z.object({
  fullName: fullNameSchema,
  email: emailSchema,
  password: newPasswordSchema,
});

export const forgotPasswordSchema = z.object({ email: emailSchema });

const confirmPasswordField = z.string().min(1, "Vui lòng nhập lại mật khẩu");

const passwordsMatch = (data: { newPassword: string; confirmPassword: string }) =>
  data.newPassword === data.confirmPassword;
const passwordsMatchError = {
  message: "Mật khẩu xác nhận không khớp",
  path: ["confirmPassword"],
};

export const resetPasswordSchema = z
  .object({
    email: emailSchema,
    otp: otpSchema,
    newPassword: newPasswordSchema,
    confirmPassword: confirmPasswordField,
  })
  .refine(passwordsMatch, passwordsMatchError);

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Vui lòng nhập mật khẩu hiện tại"),
    newPassword: newPasswordSchema,
    confirmPassword: confirmPasswordField,
  })
  .refine(passwordsMatch, passwordsMatchError)
  .refine((data) => data.newPassword !== data.currentPassword, {
    message: "Mật khẩu mới phải khác mật khẩu hiện tại",
    path: ["newPassword"],
  });

export const profileSchema = z.object({
  fullName: fullNameSchema,
  email: emailSchema,
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
export type ProfileValues = z.infer<typeof profileSchema>;
