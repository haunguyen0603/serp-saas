import {
  render,
  screen,
  fireEvent,
  within,
  cleanup,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { LanguageSelect } from "@/design-system/language-select";
import { PublicShell } from "@/design-system/public-shell";
import {
  publicLocalePairs,
  localeLanguages,
  localePath,
} from "@/lib/public-locales";
import { PricingCatalog } from "./pricing-catalog";
import type { Plan } from "@/features/billing/types";
import PricingPage, {
  metadata as pricingMetadata,
} from "@/app/vi/bang-gia/page";
import AboutPage, { metadata as aboutMetadata } from "@/app/vi/gioi-thieu/page";
import PrivacyPage, {
  metadata as privacyMetadata,
} from "@/app/vi/chinh-sach-bao-mat/page";
import TermsPage, {
  metadata as termsMetadata,
} from "@/app/vi/dieu-khoan-dich-vu/page";
import EnglishPrivacy from "@/app/(en)/privacy/page";
import EnglishTerms from "@/app/(en)/terms/page";
import AgencyArticle, { generateMetadata } from "@/app/vi/blog/[slug]/page";
import sitemap from "@/app/sitemap";

const state = vi.hoisted(() => ({
  path: "/",
  request: vi.fn(),
  authenticated: false,
}));
vi.mock("next/navigation", () => ({
  usePathname: () => state.path,
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ isAuthenticated: state.authenticated }),
}));
vi.mock("@/lib/api/client", () => ({ requestJson: state.request }));
const plans: Plan[] = (["desktop", "mobile"] as const).flatMap(
  (device, deviceIndex) =>
    (["free", "starter", "pro"] as const).map((tier, tierIndex) => ({
      id: `${device}-${tier}-id`,
      code: `${device}_${tier}`,
      name: `${device === "desktop" ? "Desktop" : "Mobile"} ${tier[0].toUpperCase()}${tier.slice(1)}`,
      device_scope: device,
      currency: "USD",
      price_monthly_minor_units:
        tierIndex === 0 ? 0 : 2950 + deviceIndex * 100 + tierIndex * 1000,
      max_projects: 1 + tierIndex,
      max_keywords: 10 + tierIndex * 123,
      monthly_keyword_checks: 25 + tierIndex * 999,
      scheduled_checks_enabled: tierIndex > 0,
      max_scheduled_frequency:
        tierIndex === 0 ? "none" : tierIndex === 1 ? "weekly" : "daily",
    })),
);
function view(component: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {component}
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  state.path = "/";
  state.authenticated = false;
  state.request.mockReset();
});
afterEach(() => vi.unstubAllEnvs());

it.each(["/", "/vi", "/pricing", "/vi/chinh-sach-bao-mat"])(
  "shows the current local flag before the language label: %s",
  (path) => {
    const vietnamese = path.startsWith("/vi");
    const { container } = render(<LanguageSelect path={path} />);
    const summary = screen.getByLabelText(/^Change language:/);
    expect(summary).toHaveAccessibleName(
      `Change language: ${vietnamese ? "Tiếng Việt" : "English"}`,
    );
    expect(summary).toHaveTextContent(vietnamese ? "Tiếng Việt" : "English");
    expect(summary.querySelector("img")).toHaveAttribute(
      "src",
      vietnamese ? "/flags/vi.svg" : "/flags/us.svg",
    );
    expect(summary.firstElementChild?.tagName).toBe("IMG");
    expect(summary.querySelector("img")).toHaveAttribute("alt", "");
    const details = container.querySelector("details")!;
    expect(details.open).toBe(false);
    fireEvent.click(summary);
    expect(details.open).toBe(true);
    expect(
      screen.getByRole("link", { name: vietnamese ? "Tiếng Việt" : "English" }),
    ).toHaveAttribute("aria-current", "page");
    fireEvent.keyDown(summary, { key: "Escape" });
    expect(details.open).toBe(false);
    expect(summary).toHaveFocus();
    fireEvent.click(summary);
    fireEvent.pointerDown(document.body);
    expect(details.open).toBe(false);
  },
);

it("falls back only for genuinely unmapped public paths and exposes both anchors in server markup", () => {
  expect(localePath("/pricing", "vi")).toBe("/vi/bang-gia");
  expect(localePath("/about", "vi")).toBe("/vi/gioi-thieu");
  expect(localePath("/unmapped", "vi")).toBe("/vi");
  const { container } = render(<LanguageSelect path="/unmapped" />);
  expect(container.querySelector('a[hreflang="en"]')).toHaveAttribute(
    "href",
    "/",
  );
  expect(container.querySelector('a[hreflang="vi"]')).toHaveAttribute(
    "href",
    "/vi",
  );
});

it("localizes every public header/footer destination while retaining app auth destinations", () => {
  state.path = "/vi/gioi-thieu";
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://serpsaas.com");
  vi.stubEnv("NEXT_PUBLIC_APP_URL", "https://app.serpsaas.com");
  render(
    <PublicShell>
      <AboutPage />
    </PublicShell>,
  );
  for (const region of ["banner", "contentinfo"] as const) {
    const links = within(
      document.querySelector<HTMLElement>(
        region === "banner" ? ".public-header" : ".public-footer",
      )!,
    );
    for (const [label, path] of [
      ["Bảng giá", "/vi/bang-gia"],
      ["Giới thiệu", "/vi/gioi-thieu"],
      ["Chính sách bảo mật", "/vi/chinh-sach-bao-mat"],
      ["Điều khoản dịch vụ", "/vi/dieu-khoan-dich-vu"],
    ]) {
      expect(links.getByRole("link", { name: label })).toHaveAttribute(
        "href",
        `https://serpsaas.com${path}`,
      );
    }
  }
  expect(screen.getByRole("link", { name: "Bắt đầu" })).toHaveAttribute(
    "href",
    "https://app.serpsaas.com/register",
  );
});

it("renders identical plan IDs, prices, limits, ordering and availability from the same API in both languages", async () => {
  // Deliberately omit a plan and reverse the response to detect locale-specific availability/order changes.
  const catalog = plans.filter((plan) => plan.code !== "mobile_pro").reverse();
  state.request.mockResolvedValue(catalog);
  const read = () =>
    Array.from(document.querySelectorAll<HTMLElement>(".pricing-card")).map(
      (card) => ({
        id: card.dataset.planId,
        name: card.getAttribute("aria-label"),
        price: card.querySelector(".pricing-price strong")!.textContent,
        limits: Array.from(card.querySelectorAll(".pricing-limits li strong"))
          .slice(0, 3)
          .map((element) => element.textContent),
        href: card.querySelector("a")!.getAttribute("href"),
      }),
    );
  view(<PricingCatalog />);
  await screen.findByRole("region", { name: "Desktop Starter" });
  const english = read();
  expect(english).toHaveLength(5);
  expect(document.body).toHaveTextContent("$39.50");
  cleanup();
  view(<PricingCatalog locale="vi" />);
  await screen.findByRole("region", { name: "Desktop Starter" });
  expect(read()).toEqual(english);
  expect(state.request.mock.calls).toEqual([
    ["/api/v1/billing/plans"],
    ["/api/v1/billing/plans"],
  ]);
  expect(document.body).toHaveTextContent("Dự án");
  expect(document.body).toHaveTextContent("Lên lịch hàng ngày");
  expect(document.body).toHaveTextContent("Lên lịch hàng tuần");
  expect(document.body).toHaveTextContent("Không hỗ trợ kiểm tra theo lịch");
  expect(document.body).not.toHaveTextContent(
    /monthly checks|Popular|Request Activation/,
  );
});

it("localizes Pricing loading/error/retry without fallback commercial data", async () => {
  state.request.mockRejectedValue(new Error("offline"));
  view(<PricingPage />);
  expect(screen.getByRole("status")).toHaveAccessibleName(
    "Đang tải các gói dịch vụ hiện hành…",
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Không thể tải danh mục gói dịch vụ chính thức",
  );
  state.request.mockResolvedValue(plans);
  fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
  expect(
    await screen.findByRole("region", { name: "Desktop Free" }),
  ).toBeVisible();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("preserves authenticated Pricing destinations while only translating presentation", async () => {
  state.authenticated = true;
  state.request.mockResolvedValue(plans);
  view(<PricingCatalog locale="vi" />);
  for (const link of await screen.findAllByRole("link", {
    name: "Yêu cầu kích hoạt",
  }))
    expect(link).toHaveAttribute("href", "/settings/billing");
  for (const link of screen.getAllByRole("link", { name: "Mở ứng dụng" }))
    expect(link).toHaveAttribute("href", "/app");
});

it.each([
  [EnglishPrivacy, PrivacyPage, "2026-10-05"],
  [EnglishTerms, TermsPage, "2026-09-20"],
] as const)(
  "retains legal section coverage, paragraph coverage and source revision date",
  (English, Vietnamese, date) => {
    let result = render(<English />);
    const structure = () =>
      Array.from(document.querySelectorAll("main section")).map((section) => ({
        id: section.getAttribute("aria-labelledby"),
        paragraphs: section.querySelectorAll("p").length,
      }));
    const source = structure();
    expect(result.container.querySelector("time")).toHaveAttribute(
      "dateTime",
      date,
    );
    result.unmount();
    result = render(<Vietnamese />);
    expect(structure()).toEqual(source);
    expect(result.container.querySelector("time")).toHaveAttribute(
      "dateTime",
      date,
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(document.body).not.toHaveTextContent(
      /phiên bản.*ưu tiên|luật Việt Nam|English version prevails/i,
    );
  },
);

it("preserves material Privacy disclosures and legal contact, with localized legal links", () => {
  render(<PrivacyPage />);
  expect(document.body).toHaveTextContent(/Serper và SerpApi/);
  expect(document.body).toHaveTextContent(/30 ngày/);
  expect(document.body).toHaveTextContent(/không có thời hạn xóa tự động/);
  expect(document.body).toHaveTextContent(/HttpOnly/);
  for (const link of screen.getAllByRole("link", {
    name: "supports@serpsaas.com",
  }))
    expect(link).toHaveAttribute("href", "mailto:supports@serpsaas.com");
  expect(
    screen.getByRole("link", { name: "Điều khoản dịch vụ" }),
  ).toHaveAttribute("href", "/vi/dieu-khoan-dich-vu");
});

it("adds the educational agency guide and keeps it distinct from the commercial page", async () => {
  const { container } = render(
    await AgencyArticle({
      params: Promise.resolve({ slug: "serp-tracking-cho-agency" }),
    }),
  );
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(document.body).toHaveTextContent(
    "Bắt đầu từ câu hỏi báo cáo của khách hàng",
  );
  expect(
    container.querySelector('main a[href="/vi/seo-rank-tracking-cho-agency"]'),
  ).not.toBeNull();
  expect(container.querySelector('main a[href="/vi/bang-gia"]')).not.toBeNull();
  expect(container.querySelector('main a[href="/pricing"]')).toBeNull();
});

it("provides self-canonical metadata and reciprocal alternates for all new pairs and includes 28 unique sitemap URLs", async () => {
  const metas = [
    pricingMetadata,
    aboutMetadata,
    privacyMetadata,
    termsMetadata,
    await generateMetadata({
      params: Promise.resolve({ slug: "serp-tracking-cho-agency" }),
    }),
  ];
  expect(new Set(metas.map((meta) => meta.description)).size).toBe(5);
  for (const meta of metas) {
    const path = new URL(String(meta.alternates?.canonical)).pathname;
    expect(meta.alternates?.languages).toEqual(localeLanguages(path));
    expect(meta.robots).toEqual({ index: true, follow: true });
    expect(meta.openGraph).toMatchObject({
      url: `https://serpsaas.com${path}`,
    });
    expect(meta.twitter).toBeDefined();
  }
  const urls = sitemap().map((page) => page.url);
  expect(new Set(urls).size).toBe(28);
  expect(urls).toHaveLength(28);
  for (const pair of publicLocalePairs)
    for (const path of [pair.en, pair.vi])
      expect(urls).toContain(`https://serpsaas.com${path}`);
});
