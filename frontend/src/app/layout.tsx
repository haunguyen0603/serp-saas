import type { Metadata } from "next";
import Link from "next/link";
import { Providers } from "@/components/providers";
import { AuthProvider } from "@/features/auth/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "SERP SaaS",
  description: "SERP SaaS development infrastructure and service health.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <div className="mx-auto max-w-3xl px-6 py-12">
          <nav
            aria-label="Main navigation"
            className="mb-16 flex gap-6 text-sm text-slate-400"
          >
            <Link href="/" className="hover:text-white">
              Home
            </Link>
            <Link href="/health" className="hover:text-white">
              Health
            </Link>
            <Link href="/signup" className="hover:text-white">
              Sign up
            </Link>
            <Link href="/login" className="hover:text-white">
              Log in
            </Link>
            <Link href="/app" className="hover:text-white">
              Account
            </Link>
            <Link href="/app/projects" className="hover:text-white">
              Projects
            </Link>
            <Link href="/app/tracked-sites" className="hover:text-white">
              Tracked Sites
            </Link>
          </nav>
          <Providers>
            <AuthProvider>{children}</AuthProvider>
          </Providers>
        </div>
      </body>
    </html>
  );
}
