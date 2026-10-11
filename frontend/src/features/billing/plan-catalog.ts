import { queryOptions } from "@tanstack/react-query";
import { requestJson } from "@/lib/api/client";
import type { Plan } from "./types";
import { formatPlanMoney } from "./money";

export const planCatalogQuery = queryOptions({
  queryKey: ["public-plans"],
  queryFn: () => requestJson<Plan[]>("/api/v1/billing/plans"),
  staleTime: 60_000,
});

const tierOrder = ["free", "starter", "pro"];

export function groupPlans(plans: Plan[]) {
  return (["desktop", "mobile"] as const).map((device) => ({
    device,
    plans: plans
      .filter((plan) => plan.device_scope === device)
      .sort(
        (a, b) =>
          tierOrder.indexOf(a.code.split("_").at(-1) ?? "") -
          tierOrder.indexOf(b.code.split("_").at(-1) ?? ""),
      ),
  }));
}

export function planPrice(plan: Plan) {
  return formatPlanMoney(plan);
}
