import { api } from "@/lib/api";
import type { User } from "@/lib/auth";

/** Roles an admin can assign; admins can't create or promote other admins. */
export type ManagedRole = "user" | "expert";

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

/** Page sizes offered by the admin list; the first is the default. Backend max is 100. */
export const PAGE_SIZES = [10, 20, 50] as const;

export type ListUsersParams = { page: number; pageSize: number; search?: string };

/** Typed wrappers around the backend /admin/users endpoints. */
export const adminUsersApi = {
  list: ({ page, pageSize, search }: ListUsersParams) => {
    const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
    if (search?.trim()) params.set("search", search.trim());
    return api<Page<User>>(`/admin/users?${params}`);
  },
  get: (id: string) => api<User>(`/admin/users/${id}`),
  create: (body: { fullName: string; email: string; password: string; role: ManagedRole }) =>
    api<User>("/admin/users", { method: "POST", json: body }),
  update: (id: string, body: { fullName?: string; email?: string; password?: string; role?: ManagedRole }) =>
    api<User>(`/admin/users/${id}`, { method: "PATCH", json: body }),
  setActive: (id: string, isActive: boolean) =>
    api<User>(`/admin/users/${id}/active`, { method: "PATCH", json: { isActive } }),
};
