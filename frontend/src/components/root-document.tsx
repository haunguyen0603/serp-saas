import type { Metadata } from "next";
import { PublicShell } from "@/design-system/public-shell";
import { AppShell } from "@/design-system/app-shell";
import { Providers } from "@/components/providers";
import { AuthProvider } from "@/features/auth/auth-provider";

import { getSiteUrl } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: getSiteUrl(),
  title: {
    default: "SERP SaaS",
    template: "%s | SERP SaaS",
  },
  description:
    "Track keyword rankings, manage projects and monitor your usage.",
};

export function RootDocument({
  children,
  locale = "en",
}: {
  children: React.ReactNode;
  locale?: "en" | "vi";
}) {
  return (
    <html lang={locale}>
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <Providers>
          <AuthProvider>
            {locale === "vi" ? (
              <PublicShell>{children}</PublicShell>
            ) : (
              <AppShell>{children}</AppShell>
            )}
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
