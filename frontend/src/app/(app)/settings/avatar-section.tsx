"use client";

import { Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { UserAvatar } from "@/components/user-avatar";
import { authApi } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

import { SettingsSection } from "./settings-section";

// Same limits as the backend (AVATAR_MAX_BYTES, accepted formats)
const MAX_BYTES = 2 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

export function AvatarSection() {
  const { user, setUser } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<"upload" | "delete" | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  async function upload(file: File) {
    setProblem(null);
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setProblem("Chỉ hỗ trợ ảnh PNG, JPG, WebP hoặc GIF.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setProblem("Ảnh vượt quá 2 MB. Vui lòng chọn ảnh nhỏ hơn.");
      return;
    }
    setPending("upload");
    try {
      setUser(await authApi.uploadAvatar(file));
      toast.success("Đã cập nhật ảnh đại diện");
    } catch (error) {
      setProblem(
        errorMessage(error, {
          413: "Ảnh vượt quá 2 MB. Vui lòng chọn ảnh nhỏ hơn.",
          415: "Tệp không phải ảnh hợp lệ. Chỉ hỗ trợ PNG, JPG, WebP hoặc GIF.",
        }),
      );
    } finally {
      setPending(null);
    }
  }

  async function remove() {
    setProblem(null);
    setPending("delete");
    try {
      setUser(await authApi.deleteAvatar());
      toast.success("Đã xoá ảnh đại diện");
    } catch (error) {
      setProblem(errorMessage(error));
    } finally {
      setPending(null);
    }
  }

  return (
    <SettingsSection title="Ảnh đại diện" description="Ảnh hiển thị trên hồ sơ và trong các cuộc trò chuyện.">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <UserAvatar user={user} className="size-16 text-base" />
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => inputRef.current?.click()} disabled={!!pending}>
              {pending === "upload" ? <Spinner /> : <Upload />}
              {user.avatar ? "Đổi ảnh" : "Tải ảnh lên"}
            </Button>
            {user.avatar && (
              <Button variant="ghost" onClick={remove} disabled={!!pending}>
                {pending === "delete" ? <Spinner /> : <Trash2 />}
                Xoá ảnh
              </Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground">PNG, JPG, WebP hoặc GIF, tối đa 2 MB.</p>
          {problem && (
            <p role="alert" className="text-sm text-destructive">
              {problem}
            </p>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = ""; // allow picking the same file again
            if (file) upload(file);
          }}
        />
      </div>
    </SettingsSection>
  );
}
