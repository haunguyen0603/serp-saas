"use client";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/auth-provider";
import { alertKeys, unreadCount } from "./api";

export function RankingAlertUnreadBadge() {
  const auth = useAuth();
  const query = useQuery({
    queryKey: [...alertKeys(auth.user?.id), "unread-count"],
    queryFn: () => unreadCount(auth.request),
    enabled:
      auth.isAuthenticated &&
      !!auth.user?.id &&
      !auth.requiresEmailVerification,
    staleTime: 60_000,
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
  return query.data?.count ? (
    <span
      className="ml-auto rounded bg-brand px-2 py-0.5 text-xs text-white"
      aria-label={`${query.data.count} unread ranking alerts`}
    >
      {query.data.count > 99 ? "99+" : query.data.count}
    </span>
  ) : null;
}
