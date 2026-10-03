"use client";

import { ChevronsUpDown, LogOut, Palette, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { Logo, LogoMark } from "@/components/logo";
import { ThemeRadioItems } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { Spinner } from "@/components/ui/spinner";
import { UserAvatar } from "@/components/user-avatar";
import { ROLE_LABELS } from "@/lib/auth";
import { visibleSections } from "@/lib/navigation";

export function AppSidebar() {
  const { user } = useAuth();
  const pathname = usePathname();
  const { isMobile, setOpenMobile } = useSidebar();

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const closeOnMobile = () => isMobile && setOpenMobile(false);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/" onClick={closeOnMobile}>
                <span className="group-data-[collapsible=icon]:hidden">
                  <Logo withSlogan />
                </span>
                <LogoMark className="hidden group-data-[collapsible=icon]:flex" />
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {visibleSections(user.role).map((section, index) => (
          <SidebarGroup key={section.label ?? index}>
            {section.label && <SidebarGroupLabel>{section.label}</SidebarGroupLabel>}
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)} tooltip={item.title}>
                      <Link href={item.href} onClick={closeOnMobile}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <NavUser onNavigate={closeOnMobile} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function NavUser({ onNavigate }: { onNavigate: () => void }) {
  const { user, logout } = useAuth();
  const { isMobile } = useSidebar();
  const [loggingOut, setLoggingOut] = useState(false);

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent">
              <UserAvatar user={user} className="size-8" />
              <span className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{user.fullName}</span>
                <span className="truncate text-xs text-muted-foreground">{user.email}</span>
              </span>
              <ChevronsUpDown className="ml-auto size-4 text-muted-foreground" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-60"
            side={isMobile ? "bottom" : "right"}
            align="end"
            sideOffset={4}
          >
            <DropdownMenuLabel className="flex items-center gap-2.5 font-normal">
              <UserAvatar user={user} className="size-8" />
              <span className="grid flex-1 text-sm leading-tight">
                <span className="truncate font-medium">{user.fullName}</span>
                <span className="truncate text-xs text-muted-foreground">{user.email}</span>
              </span>
              {user.role !== "user" && (
                <Badge variant="secondary" className="shrink-0">
                  {ROLE_LABELS[user.role]}
                </Badge>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem asChild>
                <Link href="/settings" onClick={onNavigate}>
                  <UserRound />
                  Tài khoản
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <Palette />
                  Giao diện
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  <ThemeRadioItems />
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              disabled={loggingOut}
              onSelect={(event) => {
                event.preventDefault(); // keep the menu open to show progress
                setLoggingOut(true);
                logout();
              }}
            >
              {loggingOut ? <Spinner /> : <LogOut />}
              {loggingOut ? "Đang đăng xuất…" : "Đăng xuất"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
