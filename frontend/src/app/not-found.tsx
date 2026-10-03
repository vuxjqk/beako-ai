import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center">
      <p className="text-sm font-medium text-primary">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">Không tìm thấy trang</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        Trang bạn tìm không tồn tại hoặc bạn không có quyền truy cập.
      </p>
      <Button asChild variant="outline">
        <Link href="/">Về trang chủ</Link>
      </Button>
    </main>
  );
}
