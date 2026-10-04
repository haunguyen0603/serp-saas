"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AuthSession } from "./session";
import { shouldRestoreSession } from "@/lib/site";

const AuthContext = createContext<AuthSession | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session] = useState(() => new AuthSession(() => queryClient.clear()));
  useEffect(() => {
    if (shouldRestoreSession(window.location.host)) session.start();
  }, [session]);
  return (
    <AuthContext.Provider value={session}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const session = useContext(AuthContext);
  if (!session) throw new Error("useAuth requires AuthProvider");
  const state = useSyncExternalStore(
    session.subscribe,
    session.getSnapshot,
    session.getServerSnapshot,
  );
  return {
    ...state,
    isAuthenticated: state.status === "authenticated",
    isLoading: state.status === "loading",
    requiresEmailVerification:
      state.emailVerificationRequired &&
      !!state.user &&
      !state.user.email_verified,
    login: session.login,
    register: session.register,
    logout: session.logout,
    refresh: session.refresh,
    request: session.authenticatedRequest,
    download: session.authenticatedDownload,
    getCurrentUser: session.getCurrentUser,
  };
}
