import { api } from "@/lib/api";

export type UserRole = "user" | "expert" | "admin";

export type User = {
  id: string;
  fullName: string;
  email: string;
  emailVerifiedAt: string | null;
  avatar: string | null;
  role: UserRole;
  isActive: boolean;
  hasPassword: boolean;
  googleLinked: boolean;
  createdAt: string;
};

type Message = { message: string };

/** Typed wrappers around the backend /auth endpoints. */
export const authApi = {
  login: (body: { email: string; password: string }) =>
    api<User>("/auth/login", { method: "POST", json: body, auth: false }),
  register: (body: { fullName: string; email: string; password: string }) =>
    api<User>("/auth/register", { method: "POST", json: body, auth: false }),
  google: (idToken: string) =>
    api<User>("/auth/google", { method: "POST", json: { idToken }, auth: false }),
  logout: () => api("/auth/logout", { method: "POST", auth: false }),

  forgotPassword: (email: string) =>
    api<Message>("/auth/forgot-password", { method: "POST", json: { email }, auth: false }),
  resetPassword: (body: {
    email: string;
    otp: string;
    newPassword: string;
    confirmPassword: string;
  }) => api<Message>("/auth/reset-password", { method: "POST", json: body, auth: false }),

  sendVerification: () => api<Message>("/auth/email/verification/send", { method: "POST" }),
  verifyEmail: (otp: string) =>
    api<User>("/auth/email/verification/verify", { method: "POST", json: { otp } }),

  me: () => api<User>("/auth/me"),
  updateMe: (body: { fullName?: string; email?: string }) =>
    api<User>("/auth/me", { method: "PATCH", json: body }),
  changePassword: (body: { currentPassword: string; newPassword: string; confirmPassword: string }) =>
    api<Message>("/auth/me/password", { method: "PATCH", json: body }),
  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api<User>("/auth/me/avatar", { method: "PUT", formData });
  },
  deleteAvatar: () => api<User>("/auth/me/avatar", { method: "DELETE" }),
  deleteMe: () => api("/auth/me", { method: "DELETE" }),
};

/** Uploaded avatars are relative backend paths; Google avatars are absolute URLs. */
export function avatarUrl(avatar: string | null | undefined): string | undefined {
  if (!avatar) return undefined;
  return avatar.startsWith("/") ? `/api${avatar}` : avatar;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export const ROLE_LABELS: Record<UserRole, string> = {
  user: "Người dùng",
  expert: "Chuyên gia",
  admin: "Quản trị viên",
};

/** Only allow same-site relative paths as post-login redirects. */
export function safeNext(next: string | string[] | undefined): string {
  const value = Array.isArray(next) ? next[0] : next;
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return "/";
  }
  return value;
}
