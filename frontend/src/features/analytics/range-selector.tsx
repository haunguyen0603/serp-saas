import { Tabs } from "@/design-system/ui";
import type { AnalyticsRange } from "./types";

const ranges = [
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
  { value: "90d", label: "90D" },
];

export function AnalyticsRangeSelector({
  value,
  onChange,
  label = "Analytics range",
}: {
  value: AnalyticsRange;
  onChange: (value: AnalyticsRange) => void;
  label?: string;
}) {
  return (
    <Tabs
      items={ranges}
      value={value}
      onChange={(next) => onChange(next as AnalyticsRange)}
      label={label}
    />
  );
}
