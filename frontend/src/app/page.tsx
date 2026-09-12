import { HealthDashboard } from "@/components/health-dashboard";

export default function HomePage() {
  return (
    <main>
      <p className="mb-3 text-sm font-medium uppercase tracking-widest text-teal-400">
        Development foundation
      </p>
      <h1 className="mb-4 text-4xl font-semibold tracking-tight">SERP SaaS</h1>
      <p className="mb-10 text-slate-400">
        Application infrastructure and live service connectivity.
      </p>
      <HealthDashboard />
    </main>
  );
}
