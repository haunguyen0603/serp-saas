"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge, Card, ErrorState, Skeleton } from "@/design-system/ui";
import { useAuth } from "@/features/auth/auth-provider";
import type { Plan } from "@/features/billing/types";
import { requestJson } from "@/lib/api/client";
import type { PublicLocale } from "@/lib/public-locales";
import { appHref } from "@/lib/site";

const tierOrder = ["free", "starter", "pro"];
const tierCopy: Record<string, string> = {
  free: "Try the workflow with a small keyword set.",
  starter: "For freelancers, small sites and focused SEO teams.",
  pro: "For agencies and teams with higher tracking volume.",
};

export function groupPlans(plans: Plan[]) {
  return (["desktop", "mobile"] as const).map((device) => ({
    device,
    plans: plans
      .filter((plan) => plan.device_scope === device)
      .sort(
        (a, b) =>
          tierOrder.indexOf(a.code.split("_").at(-1) ?? "") -
          tierOrder.indexOf(b.code.split("_").at(-1) ?? ""),
      ),
  }));
}

function planPrice(plan: Plan) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: plan.currency,
    minimumFractionDigits: plan.price_monthly_minor_units % 100 ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(plan.price_monthly_minor_units / 100);
}

function scheduleText(plan: Plan, locale: PublicLocale) {
  if (locale === "vi") {
    if (!plan.scheduled_checks_enabled)
      return "Không hỗ trợ kiểm tra theo lịch";
    return plan.max_scheduled_frequency === "daily"
      ? "Lên lịch hàng ngày"
      : plan.max_scheduled_frequency === "weekly"
        ? "Lên lịch hàng tuần"
        : plan.max_scheduled_frequency;
  }
  if (!plan.scheduled_checks_enabled) return "No scheduled checks";
  return `${plan.max_scheduled_frequency.replace(/^./, (letter) => letter.toUpperCase())} scheduling`;
}

export function PricingCatalog({ locale = "en" }: { locale?: PublicLocale }) {
  const vi = locale === "vi";
  const text = (en: string, vietnamese: string) => (vi ? vietnamese : en);
  const vietnameseTierCopy: Record<string, string> = {
    free: "Thử quy trình với một bộ từ khóa nhỏ.",
    starter:
      "Dành cho freelancer, website nhỏ và người làm SEO với phạm vi tập trung.",
    pro: "Dành cho agency và người làm SEO cần theo dõi nhiều từ khóa hơn.",
  };
  const auth = useAuth();
  const query = useQuery({
    queryKey: ["public-plans"],
    queryFn: () => requestJson<Plan[]>("/api/v1/billing/plans"),
    staleTime: 60_000,
  });

  return (
    <main className="public-main pricing-main">
      <section className="pricing-hero" aria-labelledby="pricing-title">
        <p className="public-eyebrow">
          {text(
            "Simple, device-specific Plans",
            "Gói dịch vụ rõ ràng theo từng thiết bị",
          )}
        </p>
        <h1 id="pricing-title">
          {text(
            "Choose the capacity your rankings need.",
            "Chọn gói phù hợp với nhu cầu theo dõi thứ hạng",
          )}
        </h1>
        <p>
          {text(
            "Desktop and Mobile are independent product scopes. Start with both Free Plans, then request activation for the scope that needs more.",
            "Desktop và Mobile là hai phạm vi sản phẩm độc lập. Bắt đầu với cả hai gói Free, rồi yêu cầu kích hoạt cho thiết bị cần thêm dung lượng.",
          )}
        </p>
      </section>

      {query.isPending && (
        <Skeleton
          label={text(
            "Loading current Plans…",
            "Đang tải các gói dịch vụ hiện hành…",
          )}
          rows={6}
        />
      )}
      {query.isError && (
        <ErrorState
          title={text(
            "Current Plans are unavailable",
            "Chưa tải được các gói dịch vụ",
          )}
          retryLabel={text("Retry", "Thử lại")}
          onRetry={() => void query.refetch()}
        >
          {text(
            "We could not load the authoritative Plan catalog. Please try again; no fallback prices are being shown.",
            "Không thể tải danh mục gói dịch vụ chính thức. Vui lòng thử lại; trang không hiển thị giá thay thế.",
          )}
        </ErrorState>
      )}
      {query.data &&
        groupPlans(query.data).map(({ device, plans }) => (
          <section
            key={device}
            className="pricing-group"
            aria-labelledby={`${device}-plans`}
          >
            <div className="pricing-group-heading">
              <div>
                <p className="public-eyebrow">
                  {vi
                    ? `Kết quả tìm kiếm ${device === "desktop" ? "Desktop" : "Mobile"}`
                    : `${device} search results`}
                </p>
                <h2 id={`${device}-plans`}>
                  {vi ? "Theo dõi thứ hạng trên" : ""}{" "}
                  {device === "desktop" ? "Desktop" : "Mobile"}
                  {vi ? "" : " Rank Tracking"}
                </h2>
              </div>
              <p>
                {device === "desktop"
                  ? text(
                      "Track rankings as they appear in desktop Google searches.",
                      "Theo dõi thứ hạng trong kết quả Google trên máy tính.",
                    )
                  : text(
                      "Measure the separate mobile search experience and its limits.",
                      "Đo kết quả tìm kiếm trên điện thoại với phạm vi và hạn mức riêng.",
                    )}
              </p>
            </div>
            <div className="pricing-grid">
              {plans.map((plan) => {
                const tier = plan.code.split("_").at(-1) ?? "";
                const paid = plan.price_monthly_minor_units > 0;
                const href = auth.isAuthenticated
                  ? paid
                    ? "/settings/billing"
                    : "/app"
                  : "/register";
                const label = auth.isAuthenticated
                  ? paid
                    ? text("Request Activation", "Yêu cầu kích hoạt")
                    : text("Open App", "Mở ứng dụng")
                  : paid
                    ? text("Request Activation", "Yêu cầu kích hoạt")
                    : text("Start Free", "Bắt đầu miễn phí");
                return (
                  <Card
                    key={plan.code}
                    className={`pricing-card${tier === "starter" ? " pricing-card-featured" : ""}`}
                    aria-label={plan.name}
                    data-plan-id={plan.id}
                  >
                    <div className="pricing-card-heading">
                      <h3>{plan.name.replace(/^(Desktop|Mobile) /, "")}</h3>
                      {tier === "starter" && (
                        <Badge tone="info">{text("Popular", "Phổ biến")}</Badge>
                      )}
                    </div>
                    <p className="pricing-audience">
                      {vi ? vietnameseTierCopy[tier] : tierCopy[tier]}
                    </p>
                    <p className="pricing-price">
                      <strong>{planPrice(plan)}</strong>
                      <span>{text("/ month", "/ tháng")}</span>
                    </p>
                    <ul className="pricing-limits">
                      <li>
                        <strong>
                          {plan.max_projects.toLocaleString("en-US")}
                        </strong>{" "}
                        {vi
                          ? "Dự án"
                          : plan.max_projects === 1
                            ? "Project"
                            : "Projects"}
                      </li>
                      <li>
                        <strong>
                          {plan.max_keywords.toLocaleString("en-US")}
                        </strong>{" "}
                        {text("Keywords", "Từ khóa")}
                      </li>
                      <li>
                        <strong>
                          {plan.monthly_keyword_checks.toLocaleString("en-US")}
                        </strong>{" "}
                        {text("monthly checks", "lượt kiểm tra hàng tháng")}
                      </li>
                      <li>
                        <strong>{scheduleText(plan, locale)}</strong>
                      </li>
                    </ul>
                    <Link
                      href={appHref(href)}
                      className={
                        tier === "starter"
                          ? "ui-link-button"
                          : "pricing-card-cta"
                      }
                    >
                      {label}
                    </Link>
                  </Card>
                );
              })}
            </div>
          </section>
        ))}

      <section className="pricing-faq" aria-labelledby="faq-title">
        <div className="public-section-heading">
          <p className="public-eyebrow">
            {text("Plan details", "Chi tiết gói dịch vụ")}
          </p>
          <h2 id="faq-title">
            {text("Frequently asked questions", "Câu hỏi thường gặp")}
          </h2>
        </div>
        <div className="faq-list">
          {(vi
            ? [
                [
                  "Một lượt kiểm tra từ khóa là gì?",
                  "Một lượt kiểm tra từ khóa logic là một đơn vị mức sử dụng của khách hàng.",
                ],
                [
                  "Vì sao gói Desktop và Mobile tách biệt?",
                  "Kết quả Google trên Desktop và Mobile có thể khác nhau. Dự án, hạn mức, mức sử dụng và đăng ký gói được quản lý độc lập cho từng thiết bị.",
                ],
                [
                  "Khi nào mức sử dụng hàng tháng được đặt lại?",
                  "Gói Free tính mức sử dụng theo tháng dương lịch. Kỳ sử dụng trả phí theo kỳ đăng ký đang hoạt động hiển thị trong Billing & Usage.",
                ],
                [
                  "Có thể dùng cả Desktop và Mobile không?",
                  "Có. Mỗi tài khoản có cả hai phạm vi; đăng ký Desktop trả phí có thể dùng cùng đăng ký Mobile trả phí hoặc Free.",
                ],
                [
                  "Điều gì xảy ra khi đạt hạn mức?",
                  "Dữ liệu hiện có vẫn đọc được; việc thêm dự án, từ khóa hoặc chạy kiểm tra mới trên thiết bị đó phải chờ đến khi có dung lượng khả dụng.",
                ],
                [
                  "Có thể nâng cấp sau không?",
                  "Có. Tạo tài khoản và dùng Billing & Usage để xem hạn mức hiện tại, rồi yêu cầu thay đổi gói thủ công.",
                ],
                [
                  "Gói trả phí được kích hoạt thế nào?",
                  "Quản trị viên kích hoạt gói trả phí sau khi xác nhận chuyển khoản ngân hàng.",
                ],
              ]
            : [
                [
                  "What is a keyword check?",
                  "One logical keyword check is one customer usage unit.",
                ],
                [
                  "Why are Desktop and Mobile Plans separate?",
                  "Desktop and Mobile Google results can differ. Their Projects, limits, usage and subscriptions are managed independently.",
                ],
                [
                  "When does monthly usage reset?",
                  "Free usage follows the calendar month. Paid usage periods follow the active subscription period shown in Billing & Usage.",
                ],
                [
                  "Can I use Desktop and Mobile together?",
                  "Yes. Every account has both scopes, and a paid Desktop subscription can coexist with a paid or Free Mobile subscription.",
                ],
                [
                  "What happens when I reach a limit?",
                  "Existing data remains readable, while new Projects, Keywords or checks in that device scope wait until capacity is available.",
                ],
                [
                  "Can I upgrade later?",
                  "Yes. Create an account and use Billing & Usage to review your current limits and request a manual Plan change.",
                ],
                [
                  "How are paid Plans activated?",
                  "An administrator activates a paid Plan after confirming the bank transfer.",
                ],
              ]
          ).map(([question, answer]) => (
            <details key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="public-final-cta pricing-final-cta">
        <h2>
          {text(
            "Start with clear limits and room to grow.",
            "Bắt đầu với hạn mức rõ ràng và khả năng mở rộng",
          )}
        </h2>
        <p>
          {text(
            "Create an account to use the Free Plans or review manual upgrade options.",
            "Tạo tài khoản để dùng các gói Free hoặc xem lựa chọn nâng cấp thủ công.",
          )}
        </p>
        <Link
          href={appHref(
            auth.isAuthenticated ? "/settings/billing" : "/register",
          )}
          className="ui-link-button"
        >
          {auth.isAuthenticated
            ? text("Open Billing & Usage", "Mở Billing & Usage")
            : text("Start Free", "Bắt đầu miễn phí")}
        </Link>
      </section>
    </main>
  );
}
