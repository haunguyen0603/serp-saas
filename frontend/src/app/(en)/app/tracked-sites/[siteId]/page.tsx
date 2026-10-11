import { TrackedSiteDetail } from "@/features/tracked-sites/site-detail";
export default async function TrackedSitePage({
  params,
}: {
  params: Promise<{ siteId: string }>;
}) {
  return <TrackedSiteDetail siteId={(await params).siteId} />;
}
