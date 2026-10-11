import { LandingPage } from "@/features/marketing/landing-page";
import { vietnameseAgencyTracker } from "@/features/marketing/vietnamese-content";
import { landingMetadata } from "@/features/marketing/seo";
export const metadata = landingMetadata(vietnameseAgencyTracker);
export default function Page() {
  return <LandingPage page={vietnameseAgencyTracker} />;
}
