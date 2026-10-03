import { Users } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState, PageShell } from "@/components/page-shell";
import { RoleGate } from "@/components/role-gate";

export const metadata: Metadata = { title: "Người dùng · Beako AI" };

export default function AdminUsersPage() {
  return (
    <RoleGate roles={["admin"]}>
      <PageShell title="Người dùng" description="Quản lý tài khoản người dùng và chuyên gia.">
        <EmptyState icon={Users} title="Đang phát triển" text="Giao diện quản lý người dùng sẽ sớm có mặt." />
      </PageShell>
    </RoleGate>
  );
}
