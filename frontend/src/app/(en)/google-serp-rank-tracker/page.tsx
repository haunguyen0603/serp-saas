import { googleRankTracker } from "@/features/marketing/landing-content";
import { LandingPage } from "@/features/marketing/landing-page";
import { landingMetadata } from "@/features/marketing/seo";

export const metadata = landingMetadata(googleRankTracker);

export default function GoogleRankTrackerPage() {
  return <LandingPage page={googleRankTracker} />;
}
