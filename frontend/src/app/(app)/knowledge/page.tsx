import { Library } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState, PageShell } from "@/components/page-shell";
import { RoleGate } from "@/components/role-gate";

export const metadata: Metadata = { title: "Kho tri thức · Beako AI" };

export default function KnowledgePage() {
  return (
    <RoleGate roles={["expert", "admin"]}>
      <PageShell title="Kho tri thức" description="Tài liệu và nguồn tri thức do chuyên gia quản lý.">
        <EmptyState icon={Library} title="Đang phát triển" text="Tính năng quản lý kho tri thức sẽ sớm có mặt." />
      </PageShell>
    </RoleGate>
  );
}
