"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { Drawer, Icon, IconButton } from "./ui";
import { appHref, siteHref } from "@/lib/site";
import { LanguageSelect } from "./language-select";
import {
  localizedPublicPath,
  publicLocale,
  vietnameseProductLinks,
} from "@/lib/public-locales";
import { landingPageLinks } from "@/lib/landing-pages";

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
  const vi = publicLocale(path) === "vi";
  const text = (en: string, translated: string) => (vi ? translated : en);
  const home = vi ? "/vi" : "/";
  const blog = vi ? "/vi/blog" : "/blog";
  const localizedLabels: Record<string, string> = {
    Home: "Trang chủ",
    Pricing: "Bảng giá",
    Blog: "Blog",
    "About us": "Giới thiệu",
    "Privacy Policy": "Chính sách bảo mật",
    "Terms of Service": "Điều khoản dịch vụ",
  };
  const publicLinks = links.map((link) => ({
    ...link,
    href: localizedPublicPath(link.href, vi ? "vi" : "en"),
    label: vi ? localizedLabels[link.label] : link.label,
  }));
  const productLinks = vi ? vietnameseProductLinks : landingPageLinks;
  const [open, setOpen] = useState(false);
  const startHref = auth.isAuthenticated
    ? auth.requiresEmailVerification
      ? "/verify-email"
      : "/app"
    : "/register";
  const startLabel = auth.isAuthenticated
    ? auth.requiresEmailVerification
      ? text("Verify email", "Xác minh email")
      : text("Open App", "Mở ứng dụng")
    : text("Get Started", "Bắt đầu");
  const navigation = (
    <nav
      aria-label={text("Public navigation", "Điều hướng công khai")}
      className="public-nav"
    >
      {publicLinks.map((link) => (
        <Link
          key={link.href}
          href={siteHref(link.href)}
          aria-current={
            path === link.href ||
            (link.href === blog && path.startsWith(`${blog}/`))
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
        {text("Skip to content", "Đến nội dung")}
      </a>
      <header className="public-header">
        <div className="public-header-inner">
          <Link
            href={siteHref(home)}
            className="public-logo"
            aria-label={text("SERP SaaS home", "Trang chủ SERP SaaS")}
          >
            <span className="app-logo-mark">
              <Icon name="chart" />
            </span>
            SERP SaaS
          </Link>
          <div className="public-desktop-nav">{navigation}</div>
          <LanguageSelect path={path} />
          <div className="public-header-actions">
            {auth.isAuthenticated ? (
              <Link href={appHref("/app/settings")} className="public-login">
                {text("Account", "Tài khoản")}
              </Link>
            ) : (
              <Link href={appHref("/login")} className="public-login">
                {text("Log in", "Đăng nhập")}
              </Link>
            )}
            <Link href={appHref(startHref)} className="ui-link-button">
              {startLabel}
            </Link>
          </div>
          <IconButton
            className="public-menu-button"
            label={text("Open public navigation", "Mở menu điều hướng")}
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
            <Link href={siteHref(home)} className="public-logo">
              SERP SaaS
            </Link>
            <p>
              {text(
                "Clear Google rank tracking for focused SEO teams.",
                "Theo dõi thứ hạng Google rõ ràng cho công việc SEO.",
              )}
            </p>
          </div>
          <nav aria-label={text("Product links", "Liên kết sản phẩm")}>
            <strong>{text("Product", "Sản phẩm")}</strong>
            {publicLinks.slice(0, 2).map((link) => (
              <Link key={link.href} href={siteHref(link.href)}>
                {link.label}
              </Link>
            ))}
            {productLinks.map((link) => (
              <Link key={link.href} href={siteHref(link.href)}>
                {link.label}
              </Link>
            ))}
            {publicLinks.slice(2).map((link) => (
              <Link key={link.href} href={siteHref(link.href)}>
                {link.label}
              </Link>
            ))}
          </nav>
          <nav aria-label={text("Account links", "Liên kết tài khoản")}>
            <strong>{text("Account", "Tài khoản")}</strong>
            <Link href={appHref("/login")}>{text("Log in", "Đăng nhập")}</Link>
            <Link href={appHref("/register")}>
              {text("Create account", "Tạo tài khoản")}
            </Link>
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
            {auth.isAuthenticated
              ? text("Account", "Tài khoản")
              : text("Log in", "Đăng nhập")}
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
