import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { RoleGate } from "@/components/role-gate";
import { PAGE_SIZES } from "@/lib/admin";

import { UsersManager } from "./users-manager";

export const metadata: Metadata = { title: "Người dùng · Beako AI" };

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AdminUsersPage({ searchParams }: PageProps<"/admin/users">) {
  const params = await searchParams;
  const page = Math.max(1, Math.floor(Number(first(params.page))) || 1);
  const requestedSize = Number(first(params.pageSize));
  const pageSize = PAGE_SIZES.find((size) => size === requestedSize) ?? PAGE_SIZES[0];
  const search = (first(params.search) ?? "").trim().slice(0, 255);

  return (
    <RoleGate roles={["admin"]}>
      <PageShell
        title="Người dùng"
        description="Quản lý tài khoản người dùng và chuyên gia."
        className="max-w-5xl"
      >
        <UsersManager initial={{ page, pageSize, search }} />
      </PageShell>
    </RoleGate>
  );
}
