"use client";

import { WifiOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { LogoMark } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { SessionExpiredError } from "@/lib/api";
import { authApi, type User } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

type AuthContextValue = {
  user: User;
  setUser: (user: User) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}

type State = { status: "loading" } | { status: "ready"; user: User } | { status: "error"; message: string };

/**
 * Loads the signed-in user for the app shell. Children only render once the user
 * is known, so they can rely on `useAuth().user`.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<State>({ status: "loading" });

  const fetchUser = useCallback(() => {
    authApi.me().then(
      (user) => setState({ status: "ready", user }),
      (error) => {
        // The API client is already redirecting to /login; keep showing the loader
        if (error instanceof SessionExpiredError) return;
        setState({ status: "error", message: errorMessage(error) });
      },
    );
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const retry = () => {
    setState({ status: "loading" });
    fetchUser();
  };

  const setUser = useCallback((user: User) => setState({ status: "ready", user }), []);

  const logout = useCallback(async () => {
    // Even if the request fails, the cookies may still be valid server-side, but
    // there is nothing more the client can do; leave the app either way.
    await authApi.logout().catch(() => undefined);
    router.replace("/login");
  }, [router]);

  const value = useMemo(
    () => (state.status === "ready" ? { user: state.user, setUser, logout } : null),
    [state, setUser, logout],
  );

  if (state.status === "error") {
    return (
      <FullScreen>
        <WifiOff className="size-8 text-muted-foreground" />
        <div className="space-y-1 text-center">
          <p className="font-medium">Không tải được dữ liệu</p>
          <p className="max-w-sm text-sm text-muted-foreground">{state.message}</p>
        </div>
        <Button variant="outline" onClick={retry}>
          Thử lại
        </Button>
      </FullScreen>
    );
  }

  if (!value) {
    return (
      <FullScreen>
        <LogoMark className="size-10" />
        <Spinner className="text-muted-foreground" />
      </FullScreen>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function FullScreen({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-6">{children}</div>;
}
