export type PublicLocale = "en" | "vi";

// Explicit editorial pairs: translated slugs are never inferred from a URL.
export const publicLocalePairs = [
  { en: "/", vi: "/vi" },
  {
    en: "/google-serp-rank-tracker",
    vi: "/vi/cong-cu-kiem-tra-thu-hang-tu-khoa",
  },
  { en: "/daily-serp-tracker", vi: "/vi/theo-doi-thu-hang-tu-khoa-hang-ngay" },
  { en: "/serp-tracking-for-agencies", vi: "/vi/seo-rank-tracking-cho-agency" },
  { en: "/blog", vi: "/vi/blog" },
  {
    en: "/blog/how-to-track-google-rankings",
    vi: "/vi/blog/cach-theo-doi-thu-hang-google",
  },
  {
    en: "/blog/how-to-monitor-keyword-ranking",
    vi: "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
  },
  { en: "/pricing", vi: "/vi/bang-gia" },
  { en: "/about", vi: "/vi/gioi-thieu" },
  { en: "/privacy", vi: "/vi/chinh-sach-bao-mat" },
  { en: "/terms", vi: "/vi/dieu-khoan-dich-vu" },
  {
    en: "/blog/serp-tracking-for-agencies",
    vi: "/vi/blog/serp-tracking-cho-agency",
  },
] as const;

export function publicLocale(path: string): PublicLocale {
  return path === "/vi" || path.startsWith("/vi/") ? "vi" : "en";
}

export function localePath(path: string, locale: PublicLocale): string {
  const pair = publicLocalePairs.find(
    (pair) => pair.en === path || pair.vi === path,
  );
  return pair?.[locale] ?? (locale === "vi" ? "/vi" : "/");
}

export function localeLanguages(
  path: string,
): Record<string, string> | undefined {
  const pair = publicLocalePairs.find(
    (pair) => pair.en === path || pair.vi === path,
  );
  if (!pair) return undefined;
  return Object.fromEntries([
    ["en", `https://serpsaas.com${pair.en}`],
    ["vi", `https://serpsaas.com${pair.vi}`],
    ["x-default", `https://serpsaas.com${pair.en}`],
  ]);
}

export const vietnameseProductLinks = [
  {
    href: publicLocalePairs[1].vi,
    label: "Công cụ kiểm tra thứ hạng từ khóa",
    description: "Xem vị trí từ khóa, lịch sử và đối thủ trên cùng SERP.",
  },
  {
    href: publicLocalePairs[2].vi,
    label: "Theo dõi thứ hạng từ khóa hàng ngày",
    description:
      "Duy trì lịch kiểm tra hàng ngày hoặc hàng tuần tùy theo gói dịch vụ.",
  },
  {
    href: publicLocalePairs[3].vi,
    label: "Theo dõi từ khóa cho SEO Agency",
    description:
      "Quản lý nhiều dự án khách hàng và chuẩn bị báo cáo trong một tài khoản.",
  },
];

// Localize only an explicitly mapped URL; keep API/app and genuinely unmapped URLs intact.
export function localizedPublicPath(
  path: string,
  locale: PublicLocale,
): string {
  const pair = publicLocalePairs.find(
    (pair) => pair.en === path || pair.vi === path,
  );
  return pair?.[locale] ?? path;
}
