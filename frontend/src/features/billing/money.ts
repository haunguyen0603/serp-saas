import type { Plan } from "./types";

export function currencyDecimals(currency: string) {
  return (
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).resolvedOptions().maximumFractionDigits ?? 2
  );
}

export function formatPlanMoney(
  plan: Pick<Plan, "currency" | "price_monthly_minor_units">,
  showFractionalZeros = false,
) {
  const decimals = currencyDecimals(plan.currency);
  const scale = 10 ** decimals;
  return new Intl.NumberFormat(plan.currency === "VND" ? "vi-VN" : "en-US", {
    style: "currency",
    currency: plan.currency,
    minimumFractionDigits:
      showFractionalZeros || plan.price_monthly_minor_units % scale
        ? decimals
        : 0,
    maximumFractionDigits: decimals,
  }).format(plan.price_monthly_minor_units / scale);
}
