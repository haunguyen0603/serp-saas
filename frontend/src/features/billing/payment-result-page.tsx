"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, ErrorState, PageHeader, Skeleton } from "@/design-system/ui";
import {
  ProtectedStatus,
  useProtectedAuth,
} from "@/features/projects/protected";
import type { PaymentStatus } from "./payments";

const pending = (status: string) =>
  ["pending", "checkout_created"].includes(status);

export function PaymentResultPage({
  result,
}: {
  result: "success" | "error" | "cancel";
}) {
  const auth = useProtectedAuth();
  const router = useRouter();
  const params = useSearchParams();
  const orderId = params.get("payment_order_id");
  const verified = auth.isAuthenticated && auth.user?.email_verified === true;
  const client = useQueryClient();
  const [timedOutOrder, setTimedOutOrder] = useState<string | null>(null);
  const timedOut = Boolean(orderId && timedOutOrder === orderId);
  useEffect(() => {
    if (auth.isAuthenticated && !verified) router.replace("/verify-email");
  }, [auth.isAuthenticated, verified, router]);
  useEffect(() => {
    if (!verified || !orderId) return;
    const timer = setTimeout(() => setTimedOutOrder(orderId), 45_000);
    return () => clearTimeout(timer);
  }, [orderId, verified]);
  const payment = useQuery({
    queryKey: ["payment", auth.user?.id, orderId],
    queryFn: () =>
      auth.request<PaymentStatus>(
        `/api/v1/billing/payments/${encodeURIComponent(orderId!)}`,
      ),
    enabled: verified && Boolean(orderId),
    retry: false,
    refetchInterval: (query) =>
      !timedOut &&
      !query.state.error &&
      result === "success" &&
      query.state.data &&
      pending(query.state.data.status)
        ? 2500
        : false,
  });
  useEffect(() => {
    if (payment.data?.status === "paid") {
      for (const key of [
        "billing",
        "usage",
        "entitlements",
        "payment-options",
        "overview",
        "projects",
        "invoices",
        "invoice",
      ]) {
        void client.invalidateQueries({ queryKey: [key] });
      }
    }
  }, [payment.data?.status, client]);
  if (!auth.isAuthenticated)
    return (
      <ProtectedStatus
        status={auth.status === "authenticated" ? "loading" : auth.status}
        error={auth.error}
        retry={() => void auth.refresh().catch(() => {})}
      />
    );
  if (!verified)
    return (
      <main>
        <p role="status">Redirecting to email verification…</p>
      </main>
    );

  const state = payment.data?.status;
  let title = "Confirming payment";
  let message =
    "Waiting for payment confirmation from SePay. Your plan updates after confirmation.";
  if (state === "paid") {
    title = "Payment successful";
    message = `${payment.data!.plan_name_snapshot} payment confirmed. Your subscription has been updated.`;
  } else if (state === "review_required" || state === "voided") {
    title = "Payment needs review";
    message =
      "Please contact support with your invoice number. Your payment needs reconciliation.";
  } else if (
    state === "failed" ||
    (result === "error" && (!state || pending(state)))
  ) {
    title = "Payment was not confirmed";
    message =
      "Checkout returned an error. Your subscription will only change if SePay confirms payment.";
  } else if (
    state === "cancelled" ||
    (result === "cancel" && (!state || pending(state)))
  ) {
    title = "Checkout cancelled";
    message =
      "Your payment has not been confirmed. Your subscription has not changed from this checkout.";
  } else if (state === "expired") {
    title = "Checkout expired";
    message =
      "If you completed payment, contact support with your invoice number.";
  } else if (timedOut && state && pending(state)) {
    title = "Payment confirmation is taking longer";
    message =
      "We have not received confirmation yet. Check back later or contact support with your invoice number.";
  }
  return (
    <main className="space-y-6">
      <PageHeader title={title} description="SePay payment status" />
      {!orderId ? (
        <ErrorState title="Payment reference is missing.">
          Return to Change Plan to view your subscription.
        </ErrorState>
      ) : payment.isPending ? (
        <Skeleton label="Loading payment status…" />
      ) : payment.isError ? (
        <ErrorState
          title="Unable to load payment status."
          onRetry={() => void payment.refetch()}
        >
          Please try again to check your payment.
        </ErrorState>
      ) : (
        <Card>
          <p role="status">{message}</p>
          <p className="text-secondary">
            Invoice: {payment.data?.invoice_number}
          </p>
          <Link
            className="ui-text-link"
            href={`/app/invoices/${encodeURIComponent(orderId)}`}
          >
            View invoice
          </Link>
        </Card>
      )}
      <Link href="/app/change-plan" className="ui-button ui-button--secondary">
        Return to Change Plan
      </Link>
    </main>
  );
}
