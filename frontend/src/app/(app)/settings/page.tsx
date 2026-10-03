import type { Metadata } from "next";

import { PageShell } from "@/components/page-shell";

import { AvatarSection } from "./avatar-section";
import { DangerZone } from "./danger-zone";
import { PasswordSection } from "./password-section";
import { ProfileSection } from "./profile-section";

export const metadata: Metadata = { title: "Tài khoản · Beako AI" };

export default function SettingsPage() {
  return (
    <PageShell title="Tài khoản" description="Quản lý thông tin cá nhân và bảo mật của bạn.">
      <div className="space-y-6">
        <AvatarSection />
        <ProfileSection />
        <PasswordSection />
        <DangerZone />
      </div>
    </PageShell>
  );
}
