import { Suspense } from "react";
import { PaymentResultPage } from "@/features/billing/payment-result-page";

export default function Page() {
  return (
    <Suspense fallback={<p role="status">Loading payment status…</p>}>
      <PaymentResultPage result="error" />
    </Suspense>
  );
}
