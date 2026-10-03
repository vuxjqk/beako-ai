import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8 text-center">
      <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight">
        <Sparkles className="size-7" />
        Beako AI
      </h1>
      <p className="text-muted-foreground">Next.js + Tailwind CSS + shadcn/ui</p>
      <Button>Bắt đầu</Button>
    </main>
  );
}
