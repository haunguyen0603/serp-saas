import Link from "next/link";
import { siteHref } from "@/lib/site";
import {
  PublicDocument,
  publicPageMetadata,
} from "@/features/marketing/public-document";

const page = {
  path: "/vi/dieu-khoan-dich-vu",
  title: "Điều khoản dịch vụ | SERP SaaS",
  description:
    "Đọc Điều khoản dịch vụ SERP SaaS về trách nhiệm tài khoản, theo dõi thứ hạng, hạn mức gói dịch vụ và quy trình kích hoạt đăng ký gói.",
  heading: "Điều khoản dịch vụ",
};
export const metadata = publicPageMetadata(page);

export default function TermsPage() {
  return (
    <PublicDocument
      page={page}
      updatedAt={{ date: "2026-09-20", label: "20 tháng 9 năm 2026" }}
      introduction={
        <p>
          Các điều khoản này giải thích cách bạn được phép sử dụng SERP SaaS và
          những gì có thể kỳ vọng từ dịch vụ. Khi tạo tài khoản và chấp nhận các
          điều khoản này, bạn đồng ý tuân thủ chúng khi sử dụng SERP SaaS.
        </p>
      }
      sections={[
        {
          id: "terms-service",
          heading: "1. Dịch vụ",
          content: (
            <p>
              SERP SaaS giúp bạn theo dõi thứ hạng từ khóa Google, tổ chức dự
              án, quản lý website theo dõi và alias tên miền, đồng thời xem lại
              các lần kiểm tra thứ hạng đã hoàn tất. Desktop và Mobile là các
              môi trường theo dõi riêng biệt với gói dịch vụ và hạn mức riêng.
            </p>
          ),
        },
        {
          id: "terms-account",
          heading: "2. Tài khoản của bạn",
          content: (
            <p>
              Cung cấp thông tin tài khoản chính xác và bảo vệ thông tin đăng
              nhập. Bạn chịu trách nhiệm về hoạt động được thực hiện qua tài
              khoản của mình. Khi được yêu cầu xác minh email, hãy xác nhận địa
              chỉ email trước khi sử dụng nền tảng. Không sử dụng tài khoản của
              người khác khi chưa được phép hoặc cố gắng truy cập dữ liệu của
              khách hàng khác.
            </p>
          ),
        },
        {
          id: "terms-use",
          heading: "3. Sử dụng được phép",
          content: (
            <p>
              Sử dụng dịch vụ hợp pháp và tôn trọng quyền của người khác. Không
              cố vượt qua kiểm soát truy cập hoặc hạn mức gói dịch vụ, gây gián
              đoạn dịch vụ, đưa mã độc vào hệ thống hoặc dùng dịch vụ để thu
              thập thông tin mà bạn không được phép truy cập. Quyền truy cập có
              thể bị hạn chế để xử lý hành vi lạm dụng hoặc bảo vệ dịch vụ và
              người dùng.
            </p>
          ),
        },
        {
          id: "terms-rankings",
          heading: "4. Kết quả thứ hạng và dịch vụ bên thứ ba",
          content: (
            <>
              <p>
                Kết quả thứ hạng là ảnh chụp tại một từ khóa, thiết bị, vị trí
                và thời điểm cụ thể. Kết quả tìm kiếm có thể thay đổi và khác
                kết quả trong trình duyệt của bạn do vị trí, cá nhân hóa hoặc
                thiết lập tìm kiếm khác. Kết quả bị thiếu nghĩa là không được
                tìm thấy trong phạm vi đã kiểm tra, không có nghĩa kết quả đó
                không thể xuất hiện ở nơi khác trong kết quả tìm kiếm.
              </p>
              <p>
                Dữ liệu tìm kiếm phụ thuộc vào dịch vụ bên thứ ba và có thể bị
                chậm hoặc không khả dụng. SERP SaaS không bảo đảm một vị trí tìm
                kiếm, mức lưu lượng truy cập hay kết quả kinh doanh cụ thể.
                Google và tên của các bên thứ ba khác thuộc về chủ sở hữu tương
                ứng; việc sử dụng những tên này không ngụ ý họ chứng thực dịch
                vụ.
              </p>
            </>
          ),
        },
        {
          id: "terms-plans",
          heading: "5. Gói dịch vụ, hạn mức và mức sử dụng",
          content: (
            <>
              <p>
                Mỗi gói quy định hạn mức dự án, từ khóa và lượt kiểm tra từ khóa
                hàng tháng, cùng quyền lên lịch nếu có. Đăng ký Desktop và
                Mobile được quản lý riêng. Bạn có thể xem các gói hiện hành tại{" "}
                <Link className="ui-text-link" href={siteHref("/vi/bang-gia")}>
                  trang Bảng giá
                </Link>
                , và điều kiện đang áp dụng cùng mức sử dụng trong Billing &amp;
                Usage.
              </p>
              <p>
                Mức sử dụng được đo bằng lượt kiểm tra từ khóa logic thay vì các
                yêu cầu nội bộ đến nhà cung cấp. Việc lên lịch và chạy kiểm tra
                mới vẫn phụ thuộc vào gói đang hoạt động và hạn mức còn lại.
                Thay đổi danh mục áp dụng cho các lần kích hoạt mới; đăng ký
                hiện có giữ nguyên giá và hạn mức đã lưu, kể cả khi được gia
                hạn.
              </p>
            </>
          ),
        },
        {
          id: "terms-activation",
          heading: "6. Kích hoạt gói trả phí và thay đổi đăng ký",
          content: (
            <>
              <p>
                Gói trả phí được quản trị viên kích hoạt thủ công sau khi chuyển
                khoản ngân hàng. Chọn gói trả phí hoặc yêu cầu kích hoạt không
                tự động thu tiền hoặc kích hoạt gói. Xác nhận số tiền, hướng dẫn
                thanh toán và kỳ đăng ký với quản trị viên trước khi chuyển
                tiền.
              </p>
              <p>
                Hỏi quản trị viên phụ trách kích hoạt về thay đổi gói, gia hạn,
                hủy đăng ký và các câu hỏi về thanh toán hoặc hoàn tiền. Xem
                ngày đăng ký và các điều kiện đã được xác nhận trong Billing
                &amp; Usage. Khi đăng ký trả phí không còn hoạt động, quyền truy
                cập khả dụng phụ thuộc vào hạn mức của gói Free tương ứng.
              </p>
            </>
          ),
        },
        {
          id: "terms-data",
          heading: "7. Thông tin bạn cung cấp",
          content: (
            <p>
              Bạn chịu trách nhiệm về từ khóa, tên miền và thông tin khác mà
              mình nhập. Chỉ cung cấp thông tin bạn được phép sử dụng. Truy vấn
              và thiết lập tìm kiếm liên quan được gửi đến nhà cung cấp dữ liệu
              tìm kiếm khi cần để thực hiện kiểm tra. Tránh nhập mật khẩu, thông
              tin xác thực thanh toán hoặc thông tin cá nhân bí mật vào trường
              từ khóa hoặc tên miền.
            </p>
          ),
        },
        {
          id: "terms-availability",
          heading: "8. Khả năng truy cập và cập nhật",
          content: (
            <p>
              Bảo trì, vấn đề kỹ thuật và sự cố bên thứ ba có thể làm gián đoạn
              truy cập hoặc trì hoãn kiểm tra. Các tính năng và điều khoản này
              có thể được cập nhật khi dịch vụ phát triển. Ngày ở đầu trang xác
              định phiên bản hiện tại. Nếu có câu hỏi về các điều khoản này,
              liên hệ quản trị viên phụ trách tài khoản trước khi yêu cầu kích
              hoạt gói trả phí.
            </p>
          ),
        },
      ]}
    />
  );
}
