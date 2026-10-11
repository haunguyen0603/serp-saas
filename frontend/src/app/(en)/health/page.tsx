import { HealthDashboard } from "@/components/health-dashboard";

export default function HealthPage() {
  return (
    <main>
      <h1 className="mb-4 text-4xl font-semibold tracking-tight">
        Service health
      </h1>
      <p className="mb-10 text-slate-400">
        Connectivity checks for the API, database, and Redis.
      </p>
      <HealthDashboard />
    </main>
  );
}
