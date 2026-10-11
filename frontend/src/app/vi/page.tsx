import Link from "next/link";
import { appHref, siteHref } from "@/lib/site";
import { vietnameseProductLinks } from "@/lib/public-locales";
import {
  landingMetadata,
  landingStructuredData,
} from "@/features/marketing/seo";
import { serializeStructuredData } from "@/features/blog/seo";

const home = {
  path: "/vi",
  title: "Theo dõi thứ hạng từ khóa Google dễ dàng | SERP SaaS",
  description:
    "Theo dõi vị trí từ khóa Google, phân tích biến động, so sánh đối thủ và tạo báo cáo SEO. Quản lý dự án Desktop và Mobile riêng biệt với SERP SaaS.",
  heading: "Theo dõi thứ hạng từ khóa Google dễ dàng",
  eyebrow: "Theo dõi Google cho công việc SEO",
  lead: "Theo dõi vị trí từ khóa, phân tích biến động thứ hạng, so sánh đối thủ và tạo báo cáo SEO trên một nền tảng đơn giản.",
};
export const metadata = landingMetadata(home);

const features = [
  [
    "Vị trí và lịch sử từ khóa",
    "Xem kết quả các lần kiểm tra đã hoàn tất, URL được khớp và thời điểm quan sát. Phạm vi kiểm tra hiện tại là Top 10.",
  ],
  [
    "Biến động có bối cảnh",
    "Phân biệt tăng, giảm, giữ vị trí và xuất hiện hoặc rời khỏi phạm vi kiểm tra. Lần chạy lỗi không phải bằng chứng website mất hạng.",
  ],
  [
    "So sánh đối thủ",
    "Đối chiếu các website trong cùng dữ liệu đã lưu để chọn từ khóa cần nghiên cứu thêm. Độ bao phủ không phải thị phần hay traffic.",
  ],
  [
    "Nhóm và nhãn từ khóa",
    "Chia bộ từ khóa theo dịch vụ, khu vực hoặc chiến dịch bằng Groups và Tags, rồi lọc để xem đúng nhóm cần xử lý.",
  ],
  [
    "Lịch kiểm tra phù hợp",
    "Kiểm tra thủ công hoặc thiết lập lịch hàng ngày hay hàng tuần tùy theo gói dịch vụ và hạn mức lượt kiểm tra.",
  ],
  [
    "Báo cáo SEO",
    "Xem trước dữ liệu và xuất CSV hoặc PDF. Báo cáo tổng hợp các quan sát đã lưu trong khoảng thời gian được chọn.",
  ],
];

export default function VietnameseHome() {
  return (
    <main className="public-main landing-main">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: serializeStructuredData(landingStructuredData(home)),
        }}
      />
      <section className="landing-hero" aria-labelledby="hero-title">
        <div>
          <p className="public-eyebrow">{home.eyebrow}</p>
          <h1 id="hero-title">{home.heading}</h1>
          <p className="public-lead">{home.lead}</p>
          <div className="public-cta-row">
            <Link
              href={appHref("/register")}
              className="ui-link-button public-cta-primary"
            >
              Bắt đầu miễn phí
            </Link>
            <Link
              href={siteHref("/vi/bang-gia")}
              className="public-secondary-link"
            >
              Xem bảng giá
            </Link>
          </div>
          <p className="public-cta-note">
            Có gói Free cho Desktop và Mobile. Không cần thẻ thanh toán.
          </p>
        </div>
        <aside className="landing-workflow" aria-labelledby="setup-heading">
          <h2 id="setup-heading">Bắt đầu với bốn bước</h2>
          <ol>
            <li>Thêm website và các tên miền liên quan hợp lệ.</li>
            <li>Tạo dự án, chọn quốc gia, ngôn ngữ, vị trí và thiết bị.</li>
            <li>Thêm bộ từ khóa cần theo dõi.</li>
            <li>Chạy kiểm tra, đọc kết quả và lên lịch nếu gói hỗ trợ.</li>
          </ol>
        </aside>
      </section>
      <section
        className="public-section public-tinted"
        aria-labelledby="features-heading"
      >
        <div className="public-section-heading">
          <p className="public-eyebrow">Dữ liệu phục vụ quyết định SEO</p>
          <h2 id="features-heading">Tập trung vào những thay đổi cần chú ý</h2>
        </div>
        <div className="public-feature-grid">
          {features.map(([title, description]) => (
            <article className="ui-card public-feature" key={title}>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
      <section
        className="public-section public-split"
        aria-labelledby="environment-heading"
      >
        <div>
          <p className="public-eyebrow">SEO tại Việt Nam</p>
          <h2 id="environment-heading">
            Đo đúng môi trường người dùng tìm kiếm
          </h2>
          <p>
            Chọn Việt Nam và tiếng Việt trong dự án nếu đó là thị trường mục
            tiêu. Giữ quốc gia, ngôn ngữ, vị trí và thiết bị nhất quán để so
            sánh lịch sử có ý nghĩa.
          </p>
        </div>
        <div>
          <h2>Desktop và Mobile được theo dõi riêng</h2>
          <p>
            Kết quả Google có thể khác theo thiết bị. Desktop và Mobile có dự
            án, gói dịch vụ và hạn mức riêng. Một quan sát không đại diện cho
            mọi kết quả cá nhân hóa.
          </p>
          <Link href={siteHref("/vi/bang-gia")} className="public-text-link">
            So sánh các gói dịch vụ →
          </Link>
        </div>
      </section>
      <section className="public-section" aria-labelledby="tools-heading">
        <div className="public-section-heading">
          <h2 id="tools-heading">Chọn quy trình theo dõi phù hợp</h2>
        </div>
        <div className="public-feature-grid">
          {vietnameseProductLinks.map((link) => (
            <article className="ui-card public-feature" key={link.href}>
              <h3>
                <Link href={siteHref(link.href)}>{link.label}</Link>
              </h3>
              <p>{link.description}</p>
              <Link href={siteHref(link.href)} className="public-text-link">
                Tìm hiểu công cụ →
              </Link>
            </article>
          ))}
        </div>
      </section>
      <section className="landing-guides" aria-labelledby="guides-heading">
        <h2 id="guides-heading">Kiến thức SEO và theo dõi thứ hạng</h2>
        <p>
          Tìm hiểu cách xây dựng mốc so sánh và đọc kết quả kiểm tra từ khóa
          đúng với phạm vi dữ liệu.
        </p>
        <Link href={siteHref("/vi/blog")} className="public-text-link">
          Đọc Blog tiếng Việt →
        </Link>
      </section>
      <section className="public-final-cta" aria-labelledby="start-heading">
        <h2 id="start-heading">Bắt đầu xây dựng lịch sử thứ hạng</h2>
        <p>
          Tạo tài khoản, thêm website và chạy bộ từ khóa đầu tiên trong hạn mức
          gói Free.
        </p>
        <div className="public-cta-row">
          <Link href={appHref("/register")} className="ui-link-button">
            Bắt đầu miễn phí
          </Link>
          <Link
            href={siteHref("/vi/bang-gia")}
            className="public-secondary-link"
          >
            Xem bảng giá
          </Link>
        </div>
      </section>
    </main>
  );
}
