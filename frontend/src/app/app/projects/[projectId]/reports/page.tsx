import { ReportsPage } from "@/features/reports/reports-page";

export default async function ProjectReportsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ReportsPage projectId={projectId} />;
}
