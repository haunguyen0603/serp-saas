import Link from "next/link";
import { appHref, siteHref } from "@/lib/site";
import { SUPPORT_EMAIL, SUPPORT_EMAIL_HREF } from "@/lib/contact";
import {
  PublicDocument,
  publicPageMetadata,
} from "@/features/marketing/public-document";

const page = {
  path: "/vi/gioi-thieu",
  title: "Giới thiệu SERP SaaS | Công cụ theo dõi thứ hạng Google",
  description:
    "Tìm hiểu SERP SaaS: nền tảng theo dõi thứ hạng từ khóa Google, quản lý dự án Desktop và Mobile riêng biệt và xem lịch sử kiểm tra SEO.",
  heading: "Giới thiệu SERP SaaS",
};
export const metadata = publicPageMetadata(page);

export default function AboutPage() {
  return (
    <PublicDocument
      page={page}
      eyebrow="Nền tảng tập trung cho công việc SEO"
      introduction={
        <p className="public-lead">
          SERP SaaS giúp chủ website và người làm SEO hiểu cách website xuất
          hiện trên Google và thứ hạng thay đổi theo thời gian.
        </p>
      }
      sections={[
        {
          id: "about-purpose",
          heading: "Vì sao có SERP SaaS",
          content: (
            <p>
              Một vị trí riêng lẻ chưa nói lên toàn bộ câu chuyện. Từ khóa,
              thiết bị, vị trí tìm kiếm và thời điểm kiểm tra đều có ý nghĩa.
              Chúng tôi muốn giữ bối cảnh đó bên cạnh kết quả để bạn có thể xem
              lại thay đổi và đưa ra quyết định có cơ sở cho công việc SEO.
            </p>
          ),
        },
        {
          id: "about-workflow",
          heading: "Bạn có thể làm gì",
          content: (
            <>
              <p>
                Tổ chức từ khóa trong các dự án có quốc gia, ngôn ngữ, vị trí và
                thiết bị cụ thể. Theo dõi Desktop và Mobile riêng biệt, chạy
                kiểm tra thủ công hoặc theo lịch mà gói dịch vụ hỗ trợ, rồi xem
                lại kết quả đã hoàn tất trong lịch sử thứ hạng.
              </p>
              <p>
                Website theo dõi tập hợp các alias tên miền hiện tại và trước
                đây. Groups và Tags giúp tổ chức từ khóa; xuất CSV và PDF giúp
                bạn chia sẻ các quan sát thứ hạng ra bên ngoài nền tảng.
              </p>
              <Link
                href={siteHref("/vi/cong-cu-kiem-tra-thu-hang-tu-khoa")}
                className="public-text-link"
              >
                Tìm hiểu công cụ theo dõi thứ hạng →
              </Link>
            </>
          ),
        },
        {
          id: "about-approach",
          heading: "Kết quả và kỳ vọng rõ ràng",
          content: (
            <>
              <p>
                Mỗi lần kiểm tra hoàn tất là một ảnh chụp của một môi trường tìm
                kiếm cụ thể. Kết quả có thể khác trình duyệt của bạn và thay đổi
                giữa các lần kiểm tra. Website không được tìm thấy trong phạm vi
                đã kiểm tra vẫn có thể xuất hiện phía sau trong kết quả tìm
                kiếm.
              </p>
              <p>
                Chúng tôi hiển thị tiến trình kiểm tra, các lần chạy lỗi và mức
                sử dụng gói dịch vụ để bạn biết những gì đã chạy và dung lượng
                còn lại. SERP SaaS giúp đo thứ hạng; không bảo đảm vị trí, lưu
                lượng truy cập hay kết quả kinh doanh.
              </p>
            </>
          ),
        },
        {
          id: "about-start",
          heading: "Bắt đầu với phạm vi bạn cần theo dõi",
          content: (
            <>
              <p>
                Mỗi tài khoản bắt đầu với các gói Free cho Desktop và Mobile.
                Gói trả phí cung cấp thêm dung lượng và lựa chọn lên lịch, được
                quản trị viên kích hoạt sau khi xác nhận chuyển khoản ngân hàng.
                Xem hạn mức và giá hiện hành trước khi chọn gói.
              </p>
              <div className="public-cta-row">
                <Link href={appHref("/register")} className="ui-link-button">
                  Bắt đầu miễn phí
                </Link>
                <Link
                  href={siteHref("/vi/bang-gia")}
                  className="public-text-link"
                >
                  Xem các gói dịch vụ
                </Link>
              </div>
            </>
          ),
        },
        {
          id: "about-contact",
          heading: "Câu hỏi về dịch vụ",
          content: (
            <p>
              Để được hỗ trợ tài khoản, thay đổi gói hoặc kích hoạt gói trả phí,
              gửi email đến{" "}
              <a className="ui-text-link" href={SUPPORT_EMAIL_HREF}>
                {SUPPORT_EMAIL}
              </a>
              . Để biết chi tiết về việc sử dụng dịch vụ và cách thông tin được
              xử lý, đọc{" "}
              <Link
                className="ui-text-link"
                href={siteHref("/vi/dieu-khoan-dich-vu")}
              >
                Điều khoản dịch vụ
              </Link>{" "}
              và{" "}
              <Link
                className="ui-text-link"
                href={siteHref("/vi/chinh-sach-bao-mat")}
              >
                Chính sách bảo mật
              </Link>
              .
            </p>
          ),
        },
      ]}
    />
  );
}
