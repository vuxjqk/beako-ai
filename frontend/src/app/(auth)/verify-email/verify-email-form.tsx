"use client";

import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { AuthHeader } from "@/components/auth-header";
import { FormAlert } from "@/components/form-alert";
import { OtpInput } from "@/components/otp-input";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useCountdown } from "@/hooks/use-countdown";
import { ApiError } from "@/lib/api";
import { authApi, type User } from "@/lib/auth";
import { errorMessage, isStatus } from "@/lib/errors";

const RESEND_COOLDOWN = 60;

export function VerifyEmailForm({ alreadySent, next }: { alreadySent: boolean; next: string }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sent, setSent] = useState(alreadySent);
  const [sending, setSending] = useState(false);
  const [otp, setOtp] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const cooldown = useCountdown(alreadySent ? RESEND_COOLDOWN : 0);

  useEffect(() => {
    authApi.me().then(setUser, (error) => setLoadError(errorMessage(error)));
  }, []);

  function finish() {
    toast.success("Email đã được xác thực");
    router.replace(next);
  }

  async function sendCode() {
    setProblem(null);
    setSending(true);
    try {
      await authApi.sendVerification();
      setSent(true);
      setOtp("");
      cooldown.start(RESEND_COOLDOWN);
      toast.success("Đã gửi mã xác thực tới email của bạn");
    } catch (error) {
      if (isStatus(error, 409)) return finish();
      if (isStatus(error, 429)) {
        // A code was sent recently; let the user enter it while the cooldown runs
        setSent(true);
        cooldown.start((error as ApiError).retryAfter ?? RESEND_COOLDOWN);
      }
      setProblem(errorMessage(error));
    } finally {
      setSending(false);
    }
  }

  async function verify(code: string) {
    setProblem(null);
    setVerifying(true);
    try {
      await authApi.verifyEmail(code);
      finish();
    } catch (error) {
      if (isStatus(error, 409)) return finish();
      setProblem(errorMessage(error, { 400: "Mã không đúng hoặc đã hết hạn. Vui lòng thử lại." }));
      setOtp("");
      setVerifying(false);
    }
  }

  if (loadError) {
    return (
      <FormAlert variant="error" title="Không tải được thông tin tài khoản">
        {loadError}
      </FormAlert>
    );
  }

  if (!user) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );
  }

  if (user.emailVerifiedAt) {
    return (
      <div className="flex flex-col items-center text-center">
        <MailCheck className="mb-4 size-10 text-primary" />
        <AuthHeader title="Email đã được xác thực" description={user.email} />
        <Button asChild className="w-full">
          <Link href={next}>Tiếp tục</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      <AuthHeader
        title="Xác thực email"
        description={
          sent ? (
            <>
              Nhập mã 6 số đã gửi tới <span className="font-medium text-foreground">{user.email}</span>.
              Mã có hiệu lực trong 10 phút.
            </>
          ) : (
            <>
              Chúng tôi sẽ gửi mã xác thực tới{" "}
              <span className="font-medium text-foreground">{user.email}</span>.
            </>
          )
        }
      />

      {problem && (
        <FormAlert className="mb-5" variant="error">
          {problem}
        </FormAlert>
      )}

      {sent ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (otp.length === 6) verify(otp);
          }}
          className="space-y-5"
        >
          <OtpInput
            value={otp}
            onChange={(value) => {
              setOtp(value);
              if (problem) setProblem(null);
            }}
            onComplete={verify}
            disabled={verifying}
            invalid={!!problem}
            autoFocus
          />
          <Button type="submit" className="w-full" disabled={verifying || otp.length !== 6}>
            {verifying && <Spinner />}
            {verifying ? "Đang xác thực…" : "Xác thực"}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Không nhận được mã?{" "}
            {cooldown.active ? (
              <span>Gửi lại sau {cooldown.seconds}s</span>
            ) : (
              <button
                type="button"
                onClick={sendCode}
                disabled={sending}
                className="font-medium text-foreground underline-offset-4 hover:underline disabled:opacity-50"
              >
                {sending ? "Đang gửi…" : "Gửi lại mã"}
              </button>
            )}
          </p>
        </form>
      ) : (
        <Button className="w-full" onClick={sendCode} disabled={sending}>
          {sending && <Spinner />}
          {sending ? "Đang gửi…" : "Gửi mã xác thực"}
        </Button>
      )}

      <p className="mt-6 text-center text-sm">
        <Link href="/" className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline">
          Để sau
        </Link>
      </p>
    </>
  );
}
