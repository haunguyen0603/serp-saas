import { LandingPage } from "@/features/marketing/landing-page";
import { vietnameseDailyTracker } from "@/features/marketing/vietnamese-content";
import { landingMetadata } from "@/features/marketing/seo";
export const metadata = landingMetadata(vietnameseDailyTracker);
export default function Page() {
  return <LandingPage page={vietnameseDailyTracker} />;
}
