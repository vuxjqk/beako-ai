"use client";

import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { conversationIdFromPath, useConversations } from "@/components/conversations-provider";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  useSidebar,
} from "@/components/ui/sidebar";
import { Spinner } from "@/components/ui/spinner";
import { errorMessage } from "@/lib/errors";
import type { ConversationSummary } from "@/lib/qa";

/** Past conversations in the sidebar: open, rename, delete. Hidden when the sidebar is collapsed. */
export function ConversationHistory({ onNavigate }: { onNavigate: () => void }) {
  const { items, loaded, error, hasMore, loadingMore, loadMore } = useConversations();
  const { isMobile } = useSidebar();
  const pathname = usePathname();
  const currentId = conversationIdFromPath(pathname);
  const [renaming, setRenaming] = useState<ConversationSummary | null>(null);
  const [deleting, setDeleting] = useState<ConversationSummary | null>(null);

  return (
    <SidebarGroup className="group-data-[collapsible=icon]:hidden">
      <SidebarGroupLabel>Lịch sử</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {!loaded && Array.from({ length: 4 }, (_, i) => (
            <SidebarMenuItem key={i}>
              <SidebarMenuSkeleton />
            </SidebarMenuItem>
          ))}
          {loaded && error && !items.length && <p className="px-2 text-xs text-muted-foreground">{error}</p>}
          {loaded && !error && !items.length && (
            <p className="px-2 text-xs text-muted-foreground">Các cuộc trò chuyện của bạn sẽ hiện ở đây.</p>
          )}
          {items.map((c) => (
            <SidebarMenuItem key={c.id}>
              <SidebarMenuButton asChild isActive={c.id === currentId} tooltip={c.title}>
                <Link href={`/c/${c.id}`} onClick={onNavigate}>
                  <span>{c.title}</span>
                </Link>
              </SidebarMenuButton>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuAction showOnHover aria-label="Tùy chọn cuộc trò chuyện">
                    <MoreHorizontal />
                  </SidebarMenuAction>
                </DropdownMenuTrigger>
                <DropdownMenuContent side={isMobile ? "bottom" : "right"} align={isMobile ? "end" : "start"}>
                  <DropdownMenuItem onSelect={() => setRenaming(c)}>
                    <Pencil />
                    Đổi tên
                  </DropdownMenuItem>
                  <DropdownMenuItem variant="destructive" onSelect={() => setDeleting(c)}>
                    <Trash2 />
                    Xóa
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          ))}
          {hasMore && (
            <SidebarMenuItem>
              <SidebarMenuButton onClick={loadMore} disabled={loadingMore} className="text-muted-foreground">
                {loadingMore && <Spinner />}
                Xem thêm
              </SidebarMenuButton>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarGroupContent>

      <RenameDialog conversation={renaming} onClose={() => setRenaming(null)} />
      <DeleteDialog conversation={deleting} currentId={currentId} onClose={() => setDeleting(null)} />
    </SidebarGroup>
  );
}

function RenameDialog({ conversation, onClose }: { conversation: ConversationSummary | null; onClose: () => void }) {
  const { rename } = useConversations();
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);
  // Reset the field whenever another conversation is picked
  const [shown, setShown] = useState<ConversationSummary | null>(null);
  if (conversation && conversation !== shown) {
    setShown(conversation);
    setTitle(conversation.title);
  }

  async function save() {
    if (!shown || !title.trim()) return;
    setSaving(true);
    try {
      await rename(shown.id, title.trim());
      onClose();
    } catch (error) {
      toast.error(errorMessage(error, { 404: "Cuộc trò chuyện không còn tồn tại." }));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={!!conversation} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <DialogHeader>
            <DialogTitle>Đổi tên cuộc trò chuyện</DialogTitle>
            <DialogDescription className="sr-only">Nhập tên mới cho cuộc trò chuyện.</DialogDescription>
          </DialogHeader>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={255} autoFocus aria-label="Tên" />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Hủy
            </Button>
            <Button type="submit" disabled={saving || !title.trim()}>
              {saving && <Spinner />}
              Lưu
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DeleteDialog({
  conversation,
  currentId,
  onClose,
}: {
  conversation: ConversationSummary | null;
  currentId: string | null;
  onClose: () => void;
}) {
  const { remove } = useConversations();
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  // Keep the last target while the close animation plays
  const [shown, setShown] = useState(conversation);
  if (conversation && conversation !== shown) setShown(conversation);

  async function confirm() {
    if (!shown) return;
    setDeleting(true);
    try {
      await remove(shown.id);
      if (shown.id === currentId) router.push("/");
      onClose();
      toast.success("Đã xóa cuộc trò chuyện");
    } catch (error) {
      toast.error(errorMessage(error, { 404: "Cuộc trò chuyện không còn tồn tại." }));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AlertDialog open={!!conversation} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Xóa cuộc trò chuyện?</AlertDialogTitle>
          <AlertDialogDescription>
            “{shown?.title}” và mọi câu hỏi, câu trả lời trong đó sẽ bị xóa vĩnh viễn.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>Hủy</AlertDialogCancel>
          <Button variant="destructive" onClick={confirm} disabled={deleting}>
            {deleting && <Spinner />}
            Xóa
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
