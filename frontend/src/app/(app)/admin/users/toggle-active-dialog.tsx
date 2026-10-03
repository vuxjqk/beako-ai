"use client";

import { useState } from "react";
import { toast } from "sonner";

import { FormAlert } from "@/components/form-alert";
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
import { Spinner } from "@/components/ui/spinner";
import { adminUsersApi } from "@/lib/admin";
import type { User } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

/** Confirms locking (deactivating) or unlocking an account. */
export function ToggleActiveDialog({
  user,
  onOpenChange,
  onSaved,
}: {
  user: User | null;
  onOpenChange: (open: boolean) => void;
  onSaved: (user: User) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  // Keep the last target while the close animation plays
  const [shown, setShown] = useState(user);
  if (user && user !== shown) setShown(user);

  const locking = shown?.isActive ?? true;

  async function confirm() {
    if (!shown) return;
    setProblem(null);
    setSaving(true);
    try {
      const updated = await adminUsersApi.setActive(shown.id, !shown.isActive);
      toast.success(updated.isActive ? `Đã mở khoá ${updated.fullName}` : `Đã khoá ${updated.fullName}`);
      onSaved(updated);
    } catch (error) {
      setProblem(errorMessage(error, { 404: "Tài khoản không còn tồn tại. Hãy tải lại danh sách." }));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AlertDialog
      open={!!user}
      onOpenChange={(next) => {
        if (saving) return;
        if (!next) setProblem(null);
        onOpenChange(next);
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{locking ? "Khoá tài khoản?" : "Mở khoá tài khoản?"}</AlertDialogTitle>
          <AlertDialogDescription>
            <span className="font-medium text-foreground">{shown?.fullName}</span> ({shown?.email}){" "}
            {locking
              ? "sẽ bị đăng xuất khỏi mọi thiết bị và không thể đăng nhập cho tới khi được mở khoá."
              : "sẽ có thể đăng nhập trở lại."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {problem && <FormAlert variant="error">{problem}</FormAlert>}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={saving}>Huỷ</AlertDialogCancel>
          {/* Plain button (not AlertDialogAction) so the dialog stays open while saving */}
          <Button variant={locking ? "destructive" : "default"} onClick={confirm} disabled={saving}>
            {saving && <Spinner />}
            {locking ? "Khoá tài khoản" : "Mở khoá"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
