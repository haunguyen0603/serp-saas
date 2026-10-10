import { dailySerpTracker } from "@/features/marketing/landing-content";
import { LandingPage } from "@/features/marketing/landing-page";
import { landingMetadata } from "@/features/marketing/seo";

export const metadata = landingMetadata(dailySerpTracker);

export default function DailySerpTrackerPage() {
  return <LandingPage page={dailySerpTracker} />;
}
