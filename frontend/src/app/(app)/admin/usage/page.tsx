import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";
import { RoleGate } from "@/components/role-gate";

import { UsageReportView } from "./usage-report";

export const metadata: Metadata = { title: "Chi phí & chất lượng · Beako AI" };

export default function AdminUsagePage() {
  return (
    <RoleGate roles={["admin"]}>
      <PageShell
        title="Chi phí & chất lượng"
        description="Số câu hỏi, chi phí ước tính và chất lượng trả lời theo ngày."
        className="max-w-6xl"
      >
        <UsageReportView />
      </PageShell>
    </RoleGate>
  );
}
