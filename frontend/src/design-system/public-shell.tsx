"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { Drawer, Icon, IconButton } from "./ui";

const links = [
  { href: "/", label: "Home" },
  { href: "/pricing", label: "Pricing" },
  { href: "/terms", label: "Terms of Service" },
];

export function PublicShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const startHref = auth.isAuthenticated ? "/app" : "/register";
  const startLabel = auth.isAuthenticated ? "Open App" : "Get Started";
  const navigation = (
    <nav aria-label="Public navigation" className="public-nav">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          aria-current={path === link.href ? "page" : undefined}
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
          <Link href="/" className="public-logo" aria-label="SERP SaaS home">
            <span className="app-logo-mark">
              <Icon name="chart" />
            </span>
            SERP SaaS
          </Link>
          <div className="public-desktop-nav">{navigation}</div>
          <div className="public-header-actions">
            {auth.isAuthenticated ? (
              <Link href="/app/settings" className="public-login">
                Account
              </Link>
            ) : (
              <Link href="/login" className="public-login">
                Log in
              </Link>
            )}
            <Link href={startHref} className="ui-link-button">
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
            <Link href="/" className="public-logo">
              SERP SaaS
            </Link>
            <p>Clear Google rank tracking for focused SEO teams.</p>
          </div>
          <nav aria-label="Product links">
            <strong>Product</strong>
            <Link href="/">Home</Link>
            <Link href="/pricing">Pricing</Link>
            <Link href="/terms">Terms of Service</Link>
          </nav>
          <nav aria-label="Account links">
            <strong>Account</strong>
            <Link href="/login">Log in</Link>
            <Link href="/register">Create account</Link>
          </nav>
        </div>
        <p className="public-copyright">
          © {new Date().getFullYear()} SERP SaaS
        </p>
      </footer>
      <Drawer open={open} onClose={() => setOpen(false)} title="SERP SaaS">
        {navigation}
        <div className="public-drawer-actions">
          <Link href={auth.isAuthenticated ? "/app/settings" : "/login"}>
            {auth.isAuthenticated ? "Account" : "Log in"}
          </Link>
          <Link href={startHref} className="ui-link-button">
            {startLabel}
          </Link>
        </div>
      </Drawer>
    </div>
  );
}
