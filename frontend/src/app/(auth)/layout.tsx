import Link from "next/link";

import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="relative flex min-h-svh flex-col">
      <header className="flex h-16 items-center justify-between px-4 sm:px-6">
        <Link href="/login" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50">
          <Logo withSlogan />
        </Link>
        <ThemeToggle />
      </header>
      <main className="flex flex-1 items-start justify-center px-4 pb-16 pt-8 sm:items-center sm:pt-0">
        {/* Taller inputs/buttons on auth pages, to line up with the 40px Google button */}
        <div className="w-full max-w-sm [&_[data-slot=button]]:h-10 [&_[data-slot=input]]:h-10">
          {children}
        </div>
      </main>
      <footer className="px-4 pb-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} Beako AI
      </footer>
    </div>
  );
}
