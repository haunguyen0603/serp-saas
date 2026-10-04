import { NextRequest, NextResponse } from "next/server";
import {
  getAppUrl,
  getSiteUrl,
  hasSeparateAppDomain,
  isAppPath,
  marketingPaths,
} from "@/lib/site";

export function proxy(request: NextRequest) {
  if (!hasSeparateAppDomain()) return NextResponse.next();
  const site = getSiteUrl();
  const app = getAppUrl();
  const host = request.headers.get("host")?.toLowerCase();
  const path = request.nextUrl.pathname;
  let target: URL | undefined;

  if (host === site.host && isAppPath(path)) {
    target = new URL(app);
    target.pathname = path;
  } else if (host === app.host && path === "/") {
    target = new URL("/app", app);
  } else if (
    host === app.host &&
    (marketingPaths.includes(path) || path === "/sitemap.xml")
  ) {
    target = new URL(site);
    target.pathname = path;
  }
  if (target) {
    target.search = request.nextUrl.search;
    return NextResponse.redirect(target, 307);
  }
  if (host === app.host && path === "/robots.txt") {
    return new NextResponse("User-agent: *\nDisallow: /\n", {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "X-Robots-Tag": "noindex, nofollow",
      },
    });
  }
  const response = NextResponse.next();
  if (host === app.host || isAppPath(path)) {
    response.headers.set("X-Robots-Tag", "noindex, nofollow");
  }
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|health|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|gif|webp|ico|woff2?)$).*)",
  ],
};
