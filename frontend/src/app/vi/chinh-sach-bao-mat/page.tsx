import Link from "next/link";
import { siteHref } from "@/lib/site";
import { SUPPORT_EMAIL, SUPPORT_EMAIL_HREF } from "@/lib/contact";
import {
  PublicDocument,
  publicPageMetadata,
} from "@/features/marketing/public-document";

const page = {
  path: "/vi/chinh-sach-bao-mat",
  title: "Chính sách bảo mật | SERP SaaS",
  description:
    "Tìm hiểu cách SERP SaaS xử lý thông tin tài khoản, dữ liệu theo dõi từ khóa, cookie, báo cáo và hồ sơ đăng ký gói dịch vụ.",
  heading: "Chính sách bảo mật",
};
export const metadata = publicPageMetadata(page);
const contact = (
  <a className="ui-text-link" href={SUPPORT_EMAIL_HREF}>
    {SUPPORT_EMAIL}
  </a>
);

export default function PrivacyPage() {
  return (
    <PublicDocument
      page={page}
      updatedAt={{ date: "2026-10-05", label: "5 tháng 10 năm 2026" }}
      introduction={
        <p>
          Chính sách này giải thích cách SERP SaaS xử lý thông tin khi bạn tạo
          tài khoản, theo dõi thứ hạng Google và sử dụng báo cáo hoặc gói trả
          phí. Hãy đọc cùng với{" "}
          <Link
            className="ui-text-link"
            href={siteHref("/vi/dieu-khoan-dich-vu")}
          >
            Điều khoản dịch vụ
          </Link>
          .
        </p>
      }
      sections={[
        {
          id: "privacy-information",
          heading: "1. Thông tin được dịch vụ xử lý",
          content: (
            <>
              <p>
                Hồ sơ tài khoản gồm địa chỉ email, giá trị băm của mật khẩu,
                trạng thái tài khoản, thời điểm đăng nhập và thời điểm bạn chấp
                nhận Điều khoản dịch vụ. Mật khẩu được lưu dưới dạng giá trị băm
                thay vì văn bản thuần.
              </p>
              <p>
                Chúng tôi lưu các dự án, từ khóa, website theo dõi, alias tên
                miền, nhóm, nhãn và thiết lập tìm kiếm mà bạn cung cấp. Chúng
                tôi cũng lưu kết quả thứ hạng, lịch sử kiểm tra, trạng thái tác
                vụ, lịch chạy và báo cáo đã tạo để bạn có thể xem lại hoạt động
                theo dõi theo thời gian.
              </p>
              <p>
                Hồ sơ đăng ký gói gồm các gói bạn chọn, kỳ đăng ký, mức sử dụng
                và hạn mức. Quản trị viên có thể ghi lại mã tham chiếu thanh
                toán và ghi chú kích hoạt khi xác nhận chuyển khoản ngân hàng.
                Dịch vụ hiện sử dụng quy trình kích hoạt gói trả phí thủ công và
                không thu thập thông tin thẻ thanh toán qua trang thanh toán.
              </p>
            </>
          ),
        },
        {
          id: "privacy-use",
          heading: "2. Cách sử dụng thông tin",
          content: (
            <>
              <p>
                Chúng tôi dùng email của bạn để gửi liên kết xác minh tài khoản
                và ghi nhận khi xác minh thành công. Chúng tôi dùng thông tin
                này để xác thực tài khoản, chạy kiểm tra thứ hạng, khớp website
                của bạn trong kết quả tìm kiếm, hiển thị lịch sử, tạo báo cáo và
                quản lý đăng ký gói cùng hạn mức sử dụng. Khi tính năng gửi báo
                cáo qua email khả dụng và bạn bật lịch gửi, chúng tôi dùng email
                đã xác minh của tài khoản để gửi báo cáo.
              </p>
              <p>
                Hồ sơ kỹ thuật như đường dẫn yêu cầu, trạng thái phản hồi, thời
                gian xử lý và lỗi tác vụ giúp chẩn đoán sự cố và vận hành dịch
                vụ. Dịch vụ lưu trữ cũng có thể xử lý thông tin kết nối, chẳng
                hạn địa chỉ IP, trong nhật ký vận hành của họ.
              </p>
            </>
          ),
        },
        {
          id: "privacy-cookies",
          heading: "3. Cookie và phiên đăng nhập",
          content: (
            <>
              <p>
                Chúng tôi dùng cookie phiên làm mới thiết yếu, có thuộc tính
                HttpOnly, để duy trì đăng nhập. Token truy cập được giữ trong bộ
                nhớ ứng dụng. Đăng xuất sẽ thu hồi phiên làm mới hiện tại và xóa
                cookie của phiên đó. Chặn cookie này có thể khiến đăng nhập
                không hoạt động đúng.
              </p>
              <p>
                Ứng dụng hiện tại không có cookie quảng cáo hoặc công cụ theo
                dõi phân tích của bên thứ ba.
              </p>
            </>
          ),
        },
        {
          id: "privacy-providers",
          heading: "4. Nhà cung cấp dịch vụ và chia sẻ dữ liệu",
          content: (
            <>
              <p>
                Các lần kiểm tra thứ hạng gửi truy vấn từ khóa và thiết lập tìm
                kiếm liên quan, như quốc gia, ngôn ngữ, vị trí và thiết bị, đến
                nhà cung cấp dữ liệu tìm kiếm đã được cấu hình. Dịch vụ hỗ trợ
                Serper và SerpApi. Tránh nhập mật khẩu hoặc thông tin cá nhân bí
                mật vào trường từ khóa hoặc tên miền.
              </p>
              <p>
                Nhà cung cấp hạ tầng lưu trữ, cơ sở dữ liệu và lưu trữ tệp xử lý
                thông tin cần thiết để vận hành dịch vụ. Nếu gửi email được bật,
                nhà cung cấp email xử lý địa chỉ người nhận và nội dung hoặc tệp
                đính kèm của báo cáo. Tùy cách triển khai và nhà cung cấp, việc
                xử lý có thể diễn ra tại quốc gia khác với quốc gia của bạn.
              </p>
              <p>
                Quản trị viên tài khoản có thể truy cập thông tin cần thiết để
                quản lý khách hàng và đăng ký gói. Quyền truy cập của khách hàng
                đối với dữ liệu theo dõi và tải báo cáo bị giới hạn ở tài khoản
                sở hữu dữ liệu.
              </p>
            </>
          ),
        },
        {
          id: "privacy-retention",
          heading: "5. Lưu trữ và thời hạn lưu giữ",
          content: (
            <>
              <p>
                Hồ sơ tài khoản, đăng ký gói và lịch sử thứ hạng được lưu để hỗ
                trợ dịch vụ và các tính năng lịch sử. Xóa một từ khóa hoặc
                website theo dõi hiện tại không nhất thiết xóa các ảnh chụp dữ
                liệu đã lưu trong lịch sử thứ hạng hoặc báo cáo.
              </p>
              <p>
                Tệp báo cáo đã tạo có ngày hết hạn được hiển thị trong dịch vụ;
                thời hạn lưu giữ mặc định là 30 ngày. Tệp hết hạn được xóa qua
                tác vụ dọn dẹp chạy nền. Metadata báo cáo và hồ sơ gửi báo cáo
                có thể vẫn được giữ sau khi tệp hết hạn. Các hồ sơ khác hiện
                không có thời hạn xóa tự động.
              </p>
            </>
          ),
        },
        {
          id: "privacy-security",
          heading: "6. Bảo vệ thông tin của bạn",
          content: (
            <p>
              Dịch vụ sử dụng băm mật khẩu, kiểm tra quyền truy cập tài khoản và
              yêu cầu xác thực khi tải báo cáo để bảo vệ quyền truy cập. Giữ mật
              khẩu riêng tư và đăng xuất trên thiết bị dùng chung. Không dịch vụ
              trực tuyến nào có thể bảo đảm thông tin được an toàn tuyệt đối.
            </p>
          ),
        },
        {
          id: "privacy-choices",
          heading: "7. Lựa chọn và yêu cầu của bạn",
          content: (
            <>
              <p>
                Bạn có thể quản lý từ khóa và website theo dõi, tạm dừng lịch
                chạy và xuất thông tin thứ hạng bằng các báo cáo CSV và PDF sẵn
                có. Để sửa thông tin tài khoản, đóng tài khoản hoặc yêu cầu về
                quyền truy cập hay xóa thông tin cá nhân, gửi email đến{" "}
                {contact}. Các yêu cầu này hiện cần sự hỗ trợ của quản trị viên.
              </p>
              <p>
                Tùy pháp luật áp dụng cho bạn, bạn có thể có thêm quyền liên
                quan đến thông tin cá nhân. Chúng tôi có thể cần xác minh danh
                tính trước khi xử lý yêu cầu. Không gửi mật khẩu hoặc token đăng
                nhập khi yêu cầu hỗ trợ.
              </p>
            </>
          ),
        },
        {
          id: "privacy-updates",
          heading: "8. Câu hỏi và cập nhật chính sách",
          content: (
            <p>
              Nếu có câu hỏi về chính sách này hoặc cách thông tin được xử lý,
              liên hệ qua {contact}. Chúng tôi có thể cập nhật trang này khi
              dịch vụ thay đổi. Ngày ở trên xác định phiên bản hiện tại.
            </p>
          ),
        },
      ]}
    />
  );
}
