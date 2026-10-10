import { landingPageLinks } from "./landing-pages";

const fallbackSiteUrl = "http://localhost:3000";

function origin(value: string, name: string): URL {
  try {
    const url = new URL(value);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      (url.pathname !== "/" && url.pathname !== "")
    )
      throw new Error();
    return new URL(url.origin);
  } catch {
    throw new Error(
      `${name} must be an HTTP(S) origin without credentials, path, query or fragment`,
    );
  }
}

export function getSiteUrl(): URL {
  return origin(
    process.env.NEXT_PUBLIC_SITE_URL || fallbackSiteUrl,
    "NEXT_PUBLIC_SITE_URL",
  );
}

export function getAppUrl(): URL {
  return origin(
    process.env.NEXT_PUBLIC_APP_URL || getSiteUrl().origin,
    "NEXT_PUBLIC_APP_URL",
  );
}

// Public SEO outputs must always point to the commercial HTTPS origin,
// including builds inspected locally or through a Cloud Run preview URL.
export function getCanonicalSiteUrl(): URL {
  const configured = getSiteUrl();
  return configured.origin === "https://serpsaas.com"
    ? configured
    : new URL("https://serpsaas.com");
}

export function hasSeparateAppDomain(): boolean {
  return getSiteUrl().origin !== getAppUrl().origin;
}

function linkTo(path: string, target: URL): string {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("Site links must use an absolute local path");
  }
  const url = new URL(path, target);
  if (url.origin !== target.origin)
    throw new Error("Site link must stay on its configured origin");
  return hasSeparateAppDomain() ? url.toString() : path;
}

export function appHref(path: string): string {
  return linkTo(path, getAppUrl());
}

export function siteHref(path: string): string {
  return linkTo(path, getSiteUrl());
}

export const marketingPaths = [
  "/",
  "/pricing",
  "/about",
  "/privacy",
  "/terms",
  "/blog",
  ...landingPageLinks.map((link) => link.href),
];

export function isMarketingPath(path: string): boolean {
  return marketingPaths.includes(path) || path.startsWith("/blog/");
}

export function isAppPath(path: string): boolean {
  return [
    "/app",
    "/settings",
    "/admin",
    "/login",
    "/register",
    "/signup",
    "/verify-email",
    "/forgot-password",
    "/reset-password",
  ].some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

export function shouldRestoreSession(host: string): boolean {
  return !hasSeparateAppDomain() || host !== getSiteUrl().host;
}
