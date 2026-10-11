import { expect, it } from "vitest";
import { formatPlanMoney } from "./money";

it.each([
  [0, "0 ₫"],
  [495330, "495.330 ₫"],
  [3363030, "3.363.030 ₫"],
  [1016730, "1.016.730 ₫"],
  [5187930, "5.187.930 ₫"],
])("formats %i dong without dividing by 100", (amount, expected) => {
  const plan = { currency: "VND", price_monthly_minor_units: amount };
  expect(formatPlanMoney(plan).replaceAll("\u00a0", " ")).toBe(expected);
  expect(formatPlanMoney(plan, true).replaceAll("\u00a0", " ")).toBe(expected);
});

it("preserves cents on legacy subscription snapshots and other currencies", () => {
  expect(
    formatPlanMoney({ currency: "USD", price_monthly_minor_units: 1900 }),
  ).toBe("$19");
  expect(
    formatPlanMoney({ currency: "USD", price_monthly_minor_units: 1900 }, true),
  ).toBe("$19.00");
  expect(
    formatPlanMoney({ currency: "USD", price_monthly_minor_units: 2950 }),
  ).toBe("$29.50");
  expect(
    formatPlanMoney({ currency: "EUR", price_monthly_minor_units: 3989 }),
  ).toBe("€39.89");
});
