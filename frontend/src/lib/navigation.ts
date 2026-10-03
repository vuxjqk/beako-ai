import { Library, MessageSquare, Users, type LucideIcon } from "lucide-react";

import type { UserRole } from "@/lib/auth";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  /** Roles that can see/open this item; omitted = everyone */
  roles?: UserRole[];
};

export type NavSection = { label?: string; items: NavItem[] };

/** Single source of truth for the sidebar and for page-level role checks. */
export const NAV_SECTIONS: NavSection[] = [
  {
    items: [{ title: "Trò chuyện", href: "/", icon: MessageSquare }],
  },
  {
    label: "Chuyên gia",
    items: [{ title: "Kho tri thức", href: "/knowledge", icon: Library, roles: ["expert", "admin"] }],
  },
  {
    label: "Quản trị",
    items: [{ title: "Người dùng", href: "/admin/users", icon: Users, roles: ["admin"] }],
  },
];

export function canAccess(role: UserRole, item: Pick<NavItem, "roles">): boolean {
  return !item.roles || item.roles.includes(role);
}

export function visibleSections(role: UserRole): NavSection[] {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => canAccess(role, item)),
  })).filter((section) => section.items.length > 0);
}
