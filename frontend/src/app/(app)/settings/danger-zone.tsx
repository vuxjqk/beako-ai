"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { FormAlert } from "@/components/form-alert";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

import { SettingsSection } from "./settings-section";

export function DangerZone() {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const confirmed = confirmText.trim().toLowerCase() === user.email;

  async function deleteAccount() {
    setProblem(null);
    setDeleting(true);
    try {
      await authApi.deleteMe();
      // Leaving the (app) layout unmounts AuthProvider, discarding the account's state
      router.replace("/login?reason=account-deleted");
    } catch (error) {
      setProblem(errorMessage(error));
      setDeleting(false);
    }
  }

  return (
    <SettingsSection
      tone="danger"
      title="Xoá tài khoản"
      description="Tài khoản sẽ bị vô hiệu hoá và bạn bị đăng xuất khỏi mọi thiết bị. Thao tác này không thể tự hoàn tác."
    >
      <AlertDialog
        open={open}
        onOpenChange={(next) => {
          if (deleting) return;
          setOpen(next);
          setConfirmText("");
          setProblem(null);
        }}
      >
        <AlertDialogTrigger asChild>
          <Button variant="destructive">Xoá tài khoản</Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá tài khoản của bạn?</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn sẽ không thể đăng nhập lại bằng tài khoản này. Để xác nhận, hãy nhập email{" "}
              <span className="font-medium text-foreground">{user.email}</span>.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {problem && <FormAlert variant="error">{problem}</FormAlert>}
          <Field>
            <FieldLabel htmlFor="confirm-email" className="sr-only">
              Email xác nhận
            </FieldLabel>
            <Input
              id="confirm-email"
              autoComplete="off"
              placeholder={user.email}
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              disabled={deleting}
            />
          </Field>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Huỷ</AlertDialogCancel>
            {/* Plain button (not AlertDialogAction) so the dialog stays open while deleting */}
            <Button variant="destructive" onClick={deleteAccount} disabled={!confirmed || deleting}>
              {deleting && <Spinner />}
              Xoá vĩnh viễn
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SettingsSection>
  );
}
