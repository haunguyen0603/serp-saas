import { LandingPage } from "@/features/marketing/landing-page";
import { vietnameseRankTracker } from "@/features/marketing/vietnamese-content";
import { landingMetadata } from "@/features/marketing/seo";
export const metadata = landingMetadata(vietnameseRankTracker);
export default function Page() {
  return <LandingPage page={vietnameseRankTracker} />;
}
