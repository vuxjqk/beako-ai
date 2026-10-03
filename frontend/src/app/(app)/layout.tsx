import { cookies } from "next/headers";

import { AppSidebar } from "@/components/app-sidebar";
import { AuthProvider } from "@/components/auth-provider";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { VerifyEmailBanner } from "@/components/verify-email-banner";

// One shell for every role; the sidebar decides what each role can see.
export default async function AppLayout({ children }: LayoutProps<"/">) {
  // Remember the collapsed/expanded sidebar across reloads (cookie written by the sidebar)
  const sidebarOpen = (await cookies()).get("sidebar_state")?.value !== "false";

  return (
    <AuthProvider>
      <SidebarProvider defaultOpen={sidebarOpen}>
        <AppSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-12 shrink-0 items-center gap-2 border-b bg-background px-3">
            <SidebarTrigger />
            <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
            <span className="text-sm font-medium text-muted-foreground">Beako AI</span>
          </header>
          <VerifyEmailBanner />
          <div className="flex flex-1 flex-col">{children}</div>
        </SidebarInset>
      </SidebarProvider>
    </AuthProvider>
  );
}
