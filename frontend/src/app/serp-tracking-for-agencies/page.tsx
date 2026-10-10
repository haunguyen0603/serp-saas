import { agencySerpTracking } from "@/features/marketing/landing-content";
import { LandingPage } from "@/features/marketing/landing-page";
import { landingMetadata } from "@/features/marketing/seo";

export const metadata = landingMetadata(agencySerpTracking);

export default function AgencySerpTrackingPage() {
  return <LandingPage page={agencySerpTracking} />;
}
