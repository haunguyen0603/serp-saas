import { Suspense } from "react";
import { RankingExplorer } from "@/features/ranking-explorer/ranking-explorer";
import { Skeleton } from "@/design-system/ui";

export default async function RankingExplorerPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return (
    <Suspense fallback={<Skeleton label="Loading Ranking Explorer…" />}>
      <RankingExplorer projectId={projectId} />
    </Suspense>
  );
}
