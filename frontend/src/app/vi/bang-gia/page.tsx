import { PricingCatalog } from "@/features/marketing/pricing-catalog";
import {
  PublicPageSchema,
  publicPageMetadata,
} from "@/features/marketing/public-document";

const page = {
  path: "/vi/bang-gia",
  title: "Bảng giá SERP SaaS | Gói theo dõi thứ hạng từ khóa",
  description:
    "So sánh gói theo dõi thứ hạng Desktop và Mobile, hạn mức dự án, từ khóa, lượt kiểm tra hàng tháng và quyền lên lịch từ danh mục SERP SaaS hiện hành.",
  heading: "Chọn gói phù hợp với nhu cầu theo dõi thứ hạng",
};
export const metadata = publicPageMetadata(page);
export default function PricingPage() {
  return (
    <>
      <PublicPageSchema page={page} />
      <PricingCatalog locale="vi" />
    </>
  );
}
