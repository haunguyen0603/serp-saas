import { Skeleton } from "@/design-system/ui";
import { CompetitorsPage } from "@/features/competitors/competitors-page";
import { Suspense } from "react";

export default async function ProjectCompetitorsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return (
    <Suspense fallback={<Skeleton label="Loading Competitors…" rows={6} />}>
      <CompetitorsPage projectId={projectId} />
    </Suspense>
  );
}
