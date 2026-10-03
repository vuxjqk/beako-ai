"use client";

import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";

import { Spinner } from "@/components/ui/spinner";
import { authApi, type User } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

// GIS must be initialized once per page; the latest component's handler is kept here.
let scriptPromise: Promise<void> | null = null;
let initialized = false;
let credentialHandler: ((credential: string) => void) | null = null;

function loadGoogleScript(): Promise<void> {
  scriptPromise ??= new Promise<void>((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptPromise = null; // allow a retry on next mount
      script.remove();
      reject(new Error("Failed to load Google script"));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

type GoogleButtonProps = {
  text?: "signin_with" | "signup_with" | "continue_with";
  onSuccess: (user: User) => void;
  onError: (message: string) => void;
  disabled?: boolean;
};

export function GoogleButton({ text = "continue_with", onSuccess, onError, disabled }: GoogleButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable">(
    CLIENT_ID ? "loading" : "unavailable",
  );
  const [verifying, setVerifying] = useState(false);

  // Keep the module-level callback pointing at this instance's latest props
  useEffect(() => {
    credentialHandler = async (credential) => {
      setVerifying(true);
      try {
        onSuccess(await authApi.google(credential));
      } catch (error) {
        onError(
          errorMessage(error, {
            401: "Xác thực với Google thất bại. Vui lòng thử lại.",
            403: "Tài khoản này đã bị vô hiệu hoá. Vui lòng liên hệ quản trị viên.",
            409: "Email này đã được liên kết với một tài khoản Google khác.",
          }),
        );
        setVerifying(false);
      }
    };
  }, [onSuccess, onError]);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        const container = containerRef.current;
        const gis = window.google?.accounts.id;
        if (cancelled || !container || !gis) return;
        if (!initialized) {
          gis.initialize({
            client_id: CLIENT_ID,
            callback: ({ credential }) => credentialHandler?.(credential),
            ux_mode: "popup",
            use_fedcm_for_button: true,
          });
          initialized = true;
        }
        container.innerHTML = "";
        gis.renderButton(container, {
          type: "standard",
          theme: resolvedTheme === "dark" ? "filled_black" : "outline",
          size: "large",
          shape: "rectangular",
          text,
          logo_alignment: "center",
          width: Math.min(Math.max(container.offsetWidth, 200), 400),
          locale: "vi",
        });
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("unavailable");
          onError("Không tải được đăng nhập Google. Kiểm tra kết nối mạng hoặc trình chặn quảng cáo.");
        }
      });

    return () => {
      cancelled = true;
    };
    // onError is intentionally not a dependency: re-rendering the button on every
    // parent render would flicker.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedTheme, text]);

  if (!CLIENT_ID) {
    return (
      <div className="flex h-10 w-full items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
        Đăng nhập Google chưa được cấu hình
      </div>
    );
  }

  const busy = verifying || disabled;
  return (
    <div className="relative h-10 w-full" aria-busy={verifying}>
      <div
        ref={containerRef}
        className={busy ? "pointer-events-none opacity-40" : undefined}
        // GIS renders an iframe; keep its container from collapsing before it loads
        style={{ colorScheme: "normal" }}
      />
      {(status === "loading" || verifying) && (
        <div className="absolute inset-0 flex items-center justify-center gap-2 rounded-md border bg-background text-sm text-muted-foreground">
          <Spinner />
          {verifying ? "Đang đăng nhập với Google…" : "Đang tải Google…"}
        </div>
      )}
      {status === "unavailable" && (
        <div className="absolute inset-0 flex items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
          Đăng nhập Google không khả dụng
        </div>
      )}
    </div>
  );
}
