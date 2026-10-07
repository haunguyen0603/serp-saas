"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { Drawer, Icon, IconButton } from "./ui";
import { appHref, siteHref } from "@/lib/site";

const links = [
  { href: "/", label: "Home" },
  { href: "/pricing", label: "Pricing" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About us" },
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/terms", label: "Terms of Service" },
];

export function PublicShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const startHref = auth.isAuthenticated
    ? auth.requiresEmailVerification
      ? "/verify-email"
      : "/app"
    : "/register";
  const startLabel = auth.isAuthenticated
    ? auth.requiresEmailVerification
      ? "Verify email"
      : "Open App"
    : "Get Started";
  const navigation = (
    <nav aria-label="Public navigation" className="public-nav">
      {links.map((link) => (
        <Link
          key={link.href}
          href={siteHref(link.href)}
          aria-current={
            path === link.href ||
            (link.href === "/blog" && path.startsWith("/blog/"))
              ? "page"
              : undefined
          }
          onClick={() => setOpen(false)}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );

  return (
    <div className="public-shell">
      <a className="public-skip" href="#public-content">
        Skip to content
      </a>
      <header className="public-header">
        <div className="public-header-inner">
          <Link
            href={siteHref("/")}
            className="public-logo"
            aria-label="SERP SaaS home"
          >
            <span className="app-logo-mark">
              <Icon name="chart" />
            </span>
            SERP SaaS
          </Link>
          <div className="public-desktop-nav">{navigation}</div>
          <div className="public-header-actions">
            {auth.isAuthenticated ? (
              <Link href={appHref("/app/settings")} className="public-login">
                Account
              </Link>
            ) : (
              <Link href={appHref("/login")} className="public-login">
                Log in
              </Link>
            )}
            <Link href={appHref(startHref)} className="ui-link-button">
              {startLabel}
            </Link>
          </div>
          <IconButton
            className="public-menu-button"
            label="Open public navigation"
            icon="menu"
            variant="ghost"
            onClick={() => setOpen(true)}
          />
        </div>
      </header>
      <div id="public-content" tabIndex={-1}>
        {children}
      </div>
      <footer className="public-footer">
        <div className="public-footer-inner">
          <div>
            <Link href={siteHref("/")} className="public-logo">
              SERP SaaS
            </Link>
            <p>Clear Google rank tracking for focused SEO teams.</p>
          </div>
          <nav aria-label="Product links">
            <strong>Product</strong>
            <Link href={siteHref("/")}>Home</Link>
            <Link href={siteHref("/pricing")}>Pricing</Link>
            <Link href={siteHref("/blog")}>Blog</Link>
            <Link href={siteHref("/about")}>About us</Link>
            <Link href={siteHref("/privacy")}>Privacy Policy</Link>
            <Link href={siteHref("/terms")}>Terms of Service</Link>
          </nav>
          <nav aria-label="Account links">
            <strong>Account</strong>
            <Link href={appHref("/login")}>Log in</Link>
            <Link href={appHref("/register")}>Create account</Link>
          </nav>
        </div>
        <p className="public-copyright">
          © {new Date().getFullYear()} SERP SaaS
        </p>
      </footer>
      <Drawer open={open} onClose={() => setOpen(false)} title="SERP SaaS">
        {navigation}
        <div className="public-drawer-actions">
          <Link
            href={appHref(auth.isAuthenticated ? "/app/settings" : "/login")}
            onClick={() => setOpen(false)}
          >
            {auth.isAuthenticated ? "Account" : "Log in"}
          </Link>
          <Link
            href={appHref(startHref)}
            className="ui-link-button"
            onClick={() => setOpen(false)}
          >
            {startLabel}
          </Link>
        </div>
      </Drawer>
    </div>
  );
}
