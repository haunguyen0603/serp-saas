"use client";

import { useQueries } from "@tanstack/react-query";
import { getDatabaseHealth, getHealth, getRedisHealth } from "@/lib/api/client";
import { config } from "@/lib/config";

const services = [
  { name: "API", check: getHealth, detail: "FastAPI" },
  { name: "Database", check: getDatabaseHealth, detail: "PostgreSQL" },
  {
    name: "Redis",
    check: getRedisHealth,
    detail: "Cache & messaging foundation",
  },
] as const;

export function HealthDashboard() {
  const checks = useQueries({
    queries: services.map((service) => ({
      queryKey: ["health", service.name],
      queryFn: service.check,
      refetchInterval: 30000,
    })),
  });

  return (
    <section aria-label="Service health" className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-slate-400">
          Environment:{" "}
          <span className="text-slate-100">{config.environment}</span>
        </p>
        <button
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-400 disabled:opacity-50"
          disabled={checks.some((check) => check.isFetching)}
          onClick={() =>
            checks.forEach((check) => {
              void check.refetch();
            })
          }
        >
          Refresh status
        </button>
      </div>
      <ul
        aria-live="polite"
        className="divide-y divide-slate-800 rounded-xl border border-slate-800 bg-slate-900/50"
      >
        {services.map((service, index) => {
          const check = checks[index];
          const status = check.isPending
            ? "checking"
            : check.isError
              ? "unavailable"
              : "connected";
          return (
            <li
              key={service.name}
              className="flex items-center justify-between gap-4 p-6"
            >
              <div>
                <h2 className="font-medium">{service.name}</h2>
                <p className="mt-1 text-sm text-slate-400">{service.detail}</p>
              </div>
              <span
                aria-label={`${service.name}: ${status}`}
                className={`rounded-full px-3 py-1 text-sm ${status === "connected" ? "bg-teal-400/10 text-teal-300" : status === "unavailable" ? "bg-red-400/10 text-red-300" : "bg-slate-800 text-slate-300"}`}
              >
                {status}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="text-sm text-slate-500">
        Status refreshes every 30 seconds.
      </p>
    </section>
  );
}
