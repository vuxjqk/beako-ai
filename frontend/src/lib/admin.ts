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

/** One day of question answering, from GET /admin/usage (days start at midnight in `timezone`). */
export type UsageDay = {
  day: string;
  questions: number;
  answered: number;
  notFound: number;
  errors: number;
  rejected: number;
  users: number;
  agent: number;
  degraded: number;
  llmCalls: number;
  promptTokens: number;
  completionTokens: number;
  costUsd: number;
  costPerQuestionUsd: number | null;
  latencyAvgMs: number | null;
  latencyP95Ms: number | null;
  thumbsUp: number;
  thumbsDown: number;
  notFoundRate: number | null;
  errorRate: number | null;
  thumbsDownRate: number | null;
  ratedShare: number | null;
};

export type UsageReport = {
  timezone: string;
  days: UsageDay[];
  today: {
    /** Today in `timezone`, YYYY-MM-DD */
    date: string;
    spentUsd: number;
    budgetUsd: number | null;
    degradeAtUsd: number | null;
    /** normal | degraded (agent off) | stopped (questions refused) */
    state: "normal" | "degraded" | "stopped";
  };
  limits: {
    userPerMinute: number;
    userPerDay: number;
    userDailyTokens: number;
    userMaxConcurrent: number;
    priceInputPerMtok: number;
    priceOutputPerMtok: number;
    model: string;
  };
  topUsersToday: {
    userId: string | null;
    email: string | null;
    fullName: string | null;
    questions: number;
    rejected: number;
    tokens: number;
    costUsd: number;
  }[];
  issues: { status: "error" | "rejected" | "answered" | "not_found"; kind: string | null; count: number }[];
};

/** Days of history the usage page offers; the first is the default. Backend max is 90. */
export const USAGE_RANGES = [7, 14, 30] as const;

export const adminUsageApi = {
  report: (days: number) => api<UsageReport>(`/admin/usage?days=${days}`),
};
