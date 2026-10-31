"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { Drawer, DropdownMenu, Icon, IconButton } from "./ui";
import { PublicShell } from "./public-shell";
import { isMarketingPath } from "@/lib/site";
import { RankingAlertUnreadBadge } from "@/features/ranking-alerts/unread-badge";
const routes = [
  { label: "Overview", href: "/app", icon: "grid", group: "" },
  {
    label: "Projects",
    href: "/app/projects",
    icon: "folder",
    group: "Rank tracking",
  },
  { label: "Rankings", href: "/app/rankings", icon: "chart", group: "" },
  {
    label: "Ranking Alerts",
    href: "/app/ranking-alerts",
    icon: "chart",
    group: "",
  },
  {
    label: "Tracked Sites",
    href: "/app/tracked-sites",
    icon: "globe",
    group: "",
  },
  {
    label: "Billing & Usage",
    href: "/settings/billing",
    icon: "wallet",
    group: "Usage & billing",
  },
  {
    label: "Change Plan",
    href: "/app/change-plan",
    icon: "refresh",
    group: "",
  },
  { label: "Invoices", href: "/app/invoices", icon: "receipt", group: "" },
  { label: "Settings", href: "/app/settings", icon: "user", group: "Account" },
];
export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const auth = useAuth();
  const router = useRouter();
  const [mobile, setMobile] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    setLogoutError(null);
    try {
      await auth.logout();
      router.replace("/login");
    } catch {
      setLogoutError("Logout could not be completed. Please try again.");
    } finally {
      setLoggingOut(false);
    }
  }
  const customer =
    path === "/app" ||
    path.startsWith("/app/") ||
    path === "/settings/billing" ||
    path.startsWith("/admin/");
  useEffect(() => {
    if (customer && auth.isAuthenticated && auth.requiresEmailVerification)
      router.replace("/verify-email");
  }, [customer, auth.isAuthenticated, auth.requiresEmailVerification, router]);
  const publicSite =
    [
      "/login",
      "/register",
      "/signup",
      "/verify-email",
      "/forgot-password",
      "/reset-password",
    ].includes(path) || isMarketingPath(path);
  if (publicSite) return <PublicShell>{children}</PublicShell>;
  if (customer && auth.isAuthenticated && auth.requiresEmailVerification)
    return (
      <PublicShell>
        <main className="public-main py-12">
          <p role="status">Redirecting to email verification…</p>
        </main>
      </PublicShell>
    );
  if (!customer)
    return (
      <div className="mx-auto max-w-3xl px-6 py-12">
        <nav
          aria-label="Main navigation"
          className="mb-16 flex flex-wrap gap-6 text-sm text-slate-400"
        >
          {[
            ["/", "Home"],
            ["/health", "Health"],
            ["/signup", "Sign up"],
            ["/login", "Log in"],
            ["/app", "Account"],
            ["/app/projects", "Projects"],
            ["/app/tracked-sites", "Tracked Sites"],
          ].map(([href, label]) => (
            <Link href={href} key={href}>
              {label}
            </Link>
          ))}
        </nav>
        {children}
      </div>
    );
  const active = routes.find((route) =>
    route.href === "/app" ? path === "/app" : path.startsWith(route.href),
  );
  const navigation = (
    <nav aria-label="Customer navigation">
      {routes.map((route) => (
        <div key={route.href}>
          {route.group && <p className="app-nav-group">{route.group}</p>}
          <Link
            className="app-nav-link"
            href={route.href}
            aria-current={active?.href === route.href ? "page" : undefined}
            onClick={() => setMobile(false)}
          >
            <Icon name={route.icon} />
            {route.label}
            {route.href === "/app/ranking-alerts" && (
              <RankingAlertUnreadBadge />
            )}
          </Link>
        </div>
      ))}
      {auth.user?.is_platform_admin && (
        <>
          <p className="app-nav-group">Administration</p>
          <Link
            href="/admin/customers"
            className="app-nav-link"
            aria-current={
              path.startsWith("/admin/customers") ? "page" : undefined
            }
            onClick={() => setMobile(false)}
          >
            <Icon name="user" />
            Customers
          </Link>
          <Link
            href="/admin/plans"
            className="app-nav-link"
            aria-current={path === "/admin/plans" ? "page" : undefined}
            onClick={() => setMobile(false)}
          >
            <Icon name="wallet" />
            Plans &amp; Pricing
          </Link>
        </>
      )}
    </nav>
  );
  return (
    <div className="app-shell">
      <a className="app-skip" href="#main-content">
        Skip to content
      </a>
      <aside className="app-sidebar">
        <Link href="/app" className="app-logo">
          <span className="app-logo-mark">
            <Icon name="chart" />
          </span>
          SERP SaaS
        </Link>
        {navigation}
        <div className="app-sidebar-foot">
          Your search visibility,
          <br />
          in one place.
        </div>
      </aside>
      <div className="app-frame">
        <header className="app-topbar">
          <div className="app-breadcrumb">
            <IconButton
              className="app-mobile-trigger"
              label="Open navigation"
              icon="menu"
              variant="ghost"
              onClick={() => setMobile(true)}
            />
            <span>Workspace</span>
            <Icon name="chevron" width={14} />
            <span>
              {active?.label ??
                (path === "/admin/plans"
                  ? "Plans & Pricing"
                  : "Customer billing")}
            </span>
          </div>
          <div className="app-account">
            <span className="app-account-email text-secondary text-xs">
              {auth.user?.email}
            </span>
            <DropdownMenu label="Account">
              <Link href="/app/settings">Profile & settings</Link>
              <Link href="/settings/billing">Billing & Usage</Link>
              <button
                type="button"
                onClick={() => void logout()}
                disabled={loggingOut}
              >
                {loggingOut ? "Logging out…" : "Logout"}
              </button>
            </DropdownMenu>
          </div>
        </header>
        <div id="main-content" tabIndex={-1} className="app-content">
          {logoutError && (
            <p role="alert" className="mb-4">
              {logoutError}
            </p>
          )}
          {children}
        </div>
      </div>
      <Drawer open={mobile} onClose={() => setMobile(false)} title="SERP SaaS">
        {navigation}
      </Drawer>
    </div>
  );
}
