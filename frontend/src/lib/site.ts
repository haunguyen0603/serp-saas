const fallbackSiteUrl = "http://localhost:3000";

export function getSiteUrl(): URL {
  const value = process.env.NEXT_PUBLIC_SITE_URL || fallbackSiteUrl;
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) throw new Error();
    return new URL(url.origin);
  } catch {
    throw new Error("NEXT_PUBLIC_SITE_URL must be an HTTP(S) origin");
  }
}
