import type { LandingContent } from "./landing-content";
import { vietnameseProductLinks } from "@/lib/public-locales";

const start = {
  heading: "Bắt đầu với một dự án SEO rõ ràng",
  description:
    "Tạo tài khoản, chọn môi trường tìm kiếm và thêm nhóm từ khóa bạn muốn theo dõi.",
  label: "Bắt đầu theo dõi",
};
const baselineGuide = {
  path: "/vi/blog/cach-theo-doi-thu-hang-google",
  label: "Đọc hướng dẫn theo dõi thứ hạng Google",
  description:
    "Chọn bộ từ khóa, thiết lập môi trường tìm kiếm và xây dựng mốc so sánh cho những lần kiểm tra sau.",
};
const checkGuide = {
  path: "/vi/blog/cach-kiem-tra-thu-hang-tu-khoa",
  label: "Đọc cách kiểm tra thứ hạng từ khóa",
  description:
    "Hiểu sự khác nhau giữa kiểm tra thủ công và công cụ, đồng thời đọc kết quả đúng với phạm vi được kiểm tra.",
};

export const vietnameseRankTracker: LandingContent = {
  path: vietnameseProductLinks[0].href,
  title: "Công cụ kiểm tra thứ hạng từ khóa Google | SERP SaaS",
  description:
    "Kiểm tra thứ hạng từ khóa Google, xem lịch sử, phân tích biến động và so sánh đối thủ với SERP SaaS. Theo dõi Desktop và Mobile riêng biệt.",
  heading: "Theo dõi thứ hạng từ khóa trên Google",
  eyebrow: "Công cụ kiểm tra thứ hạng từ khóa",
  lead: "Đưa từ khóa, vị trí trên Google và lịch sử kiểm tra vào cùng một dự án để biết đâu là thay đổi cần chú ý trong công việc SEO.",
  note: "Các lần kiểm tra hiện tại bao phủ Top 10. Desktop và Mobile được theo dõi trong các dự án riêng biệt.",
  workflow: {
    heading: "Từ thiết lập đến kết quả đầu tiên",
    steps: [
      "Thêm website và các tên miền liên quan hợp lệ.",
      "Tạo dự án: chọn Việt Nam, tiếng Việt và thiết bị phù hợp nếu đó là thị trường mục tiêu.",
      "Thêm từ khóa và chạy kiểm tra.",
      "Xem vị trí, URL khớp và thời điểm kiểm tra.",
    ],
  },
  sections: [
    {
      heading: "Theo dõi vị trí từ khóa theo thời gian",
      paragraphs: [
        "Mỗi lần kiểm tra hoàn tất tạo một quan sát có thời điểm cụ thể. Bạn có thể xem lại lịch sử để đối chiếu vị trí và URL của website thay vì ghi chép rời rạc sau mỗi lần tìm kiếm.",
        "Giữ nguyên quốc gia, ngôn ngữ tìm kiếm, vị trí và thiết bị khi so sánh. Kết quả Google ở Việt Nam trên điện thoại có thể khác kết quả trên máy tính hoặc một thị trường khác.",
      ],
    },
    {
      heading: "Phân tích biến động thứ hạng",
      paragraphs: [
        "Ranking Explorer giúp phân biệt từ khóa tăng hạng, giảm hạng, giữ vị trí hoặc xuất hiện và rời khỏi phạm vi đã kiểm tra. Xem ngày của hai quan sát trước khi diễn giải mức thay đổi.",
        "Không thấy website trong một lần kiểm tra Top 10 đầy đủ chỉ cho biết website nằm ngoài phạm vi đó; không xác định được vị trí chính xác phía sau. Lần kiểm tra lỗi hoặc dữ liệu chưa đầy đủ không chứng minh website đã mất hạng.",
      ],
    },
    {
      heading: "Theo dõi đối thủ trên cùng SERP",
      paragraphs: [
        "So sánh website của bạn với các đối thủ đã chọn dựa trên cùng dữ liệu kiểm tra được lưu. Xem những từ khóa đối thủ xuất hiện để chọn trang cần phân tích thêm.",
        "Độ bao phủ thể hiện mức hiện diện trong bộ từ khóa đã kiểm tra, không phải thị phần hay lưu lượng truy cập. Dùng dữ liệu này cùng mục tiêu kinh doanh để chọn việc SEO tiếp theo.",
      ],
    },
    {
      heading: "Nhóm và lọc từ khóa",
      paragraphs: [
        "Dùng Groups để chia từ khóa theo dịch vụ, sản phẩm hoặc khu vực; dùng Tags cho chiến dịch, ý định tìm kiếm hay mức ưu tiên. Lọc danh sách để tập trung vào một câu hỏi cụ thể.",
        "Kiểm tra chế độ khớp ANY hoặc ALL của Tags để hiểu đúng tập từ khóa đang xem. Khi thêm từ khóa mới, lưu ý rằng phạm vi so sánh của báo cáo có thể thay đổi.",
      ],
    },
    {
      heading: "Xem lịch sử thứ hạng",
      paragraphs: [
        "Mở lịch sử của từ khóa để xem thời điểm, vị trí và URL được khớp trong từng lần chạy. Khoảng trống do chưa có quan sát thành công không đồng nghĩa thứ hạng giữ nguyên.",
        "Tên miền hiện tại và các alias đang hoạt động ảnh hưởng đến việc khớp website trong dữ liệu đã lưu. Khi chuyển tên miền, hãy xem lại các alias trước khi kết luận về xu hướng.",
      ],
    },
    {
      heading: "Xuất báo cáo SEO",
      paragraphs: [
        "Xuất CSV để phân tích thêm hoặc PDF để trình bày kết quả dự án. Xem trước khoảng thời gian, website và bộ lọc trước khi chia sẻ báo cáo.",
        "Nếu hệ thống đã cấu hình gửi báo cáo định kỳ, báo cáo được gửi đến email đã xác minh của chính tài khoản. Lịch gửi báo cáo và lịch kiểm tra thứ hạng là hai quy trình riêng biệt.",
      ],
    },
  ],
  midCta: { ...start, heading: "Tạo mốc so sánh cho bộ từ khóa của bạn" },
  finalCta: { ...start, heading: "Bắt đầu theo dõi thứ hạng" },
  guide: baselineGuide,
};

export const vietnameseDailyTracker: LandingContent = {
  path: vietnameseProductLinks[1].href,
  title: "Theo dõi thứ hạng từ khóa hàng ngày | SERP SaaS",
  description:
    "Theo dõi biến động thứ hạng từ khóa Google theo lịch, xem lịch sử và kiểm tra các thay đổi đáng chú ý. Lịch hàng ngày hoặc hàng tuần tùy gói dịch vụ.",
  heading: "Theo dõi thứ hạng từ khóa hàng ngày",
  eyebrow: "Duy trì nhịp kiểm tra SEO",
  lead: "Tạo lịch kiểm tra lặp lại cho bộ từ khóa quan trọng và dành thời gian đọc những thay đổi có ý nghĩa sau mỗi lần chạy.",
  note: "Lịch kiểm tra hàng ngày hoặc hàng tuần tùy theo gói dịch vụ. Phạm vi kiểm tra hiện tại là Top 10.",
  workflow: {
    heading: "Một lịch kiểm tra có thể duy trì",
    steps: [
      "Chọn bộ từ khóa và môi trường Google cố định.",
      "Thiết lập lịch hàng ngày hoặc hàng tuần nếu gói dịch vụ hỗ trợ.",
      "Xem trạng thái và thời điểm thực tế của từng lần chạy.",
      "Đối chiếu lịch sử và ưu tiên các thay đổi cần tìm hiểu.",
    ],
  },
  sections: [
    {
      heading: "Khi nào nên kiểm tra hàng ngày?",
      paragraphs: [
        "Sau khi cập nhật nội dung, ra mắt trang mới hoặc chuyển tên miền, các quan sát gần nhau giúp bạn nhận ra một thay đổi có kéo dài hay không. Chọn một nhóm từ khóa đủ nhỏ để có thể đọc và xử lý kết quả.",
        "Theo dõi hàng tuần có thể phù hợp với dự án ổn định hơn. Tăng tần suất tạo thêm mốc dữ liệu, nhưng không tự giải thích nguyên nhân thay đổi hay đảm bảo kết quả SEO tốt hơn.",
      ],
    },
    {
      heading: "Chọn lịch phù hợp với gói dịch vụ",
      paragraphs: [
        "Khả năng lên lịch và số lượt kiểm tra phụ thuộc vào gói dịch vụ. Xem Bảng giá hiện hành trước khi mở rộng số từ khóa hoặc chuyển sang lịch hàng ngày.",
        "Desktop và Mobile có dự án, gói dịch vụ và hạn mức riêng. Bạn vẫn có thể chạy kiểm tra thủ công khi cần một quan sát cụ thể trong phạm vi hạn mức của tài khoản.",
      ],
    },
    {
      heading: "Đọc thay đổi giữa các lần kiểm tra",
      paragraphs: [
        "Lọc Ranking Explorer theo nhóm, nhãn hoặc loại biến động để tập trung vào chiến dịch đang theo dõi. Xem cả URL đích và vị trí; một từ khóa có thể được khớp với trang khác trong website.",
        "Ngày không có lần kiểm tra thành công là khoảng trống dữ liệu. Hãy dùng các mốc thực tế được hiển thị thay vì giả định rằng mỗi ngày đều có số liệu mới.",
      ],
    },
    {
      heading: "Tìm hiểu những lần giảm hạng",
      paragraphs: [
        "Trước tiên xem lần chạy có hoàn tất hay không, sau đó mở lịch sử và so sánh đối thủ trong cùng dữ liệu. Giữ quốc gia, ngôn ngữ, vị trí và thiết bị nhất quán để việc đối chiếu có ý nghĩa.",
        "Nếu website không còn xuất hiện trong Top 10 của một lần kiểm tra đầy đủ, vị trí phía sau chưa được xác định. Kết hợp Search Console, dữ liệu truy cập và việc kiểm tra trang để tìm nguyên nhân; một quan sát đơn lẻ chưa đủ để kết luận.",
      ],
    },
    {
      heading: "Giữ báo cáo nhất quán",
      paragraphs: [
        "Dùng cùng khoảng thời gian và bộ từ khóa khi xuất CSV hoặc PDF cho các kỳ báo cáo. Ghi nhận việc thêm từ khóa hay thay đổi alias để người đọc hiểu phạm vi so sánh.",
        "Báo cáo tổng hợp các quan sát đã lưu. Lịch gửi email, nếu được cấu hình, gửi đến email đã xác minh của tài khoản và không bảo đảm có lần đo mới cho từng ngày trong báo cáo.",
      ],
    },
  ],
  midCta: { ...start, heading: "Chọn nhịp theo dõi bạn có thể sử dụng" },
  finalCta: { ...start, heading: "Bắt đầu theo dõi biến động từ khóa" },
  guide: checkGuide,
};

export const vietnameseAgencyTracker: LandingContent = {
  path: vietnameseProductLinks[2].href,
  title: "Theo dõi thứ hạng từ khóa cho SEO Agency | SERP SaaS",
  description:
    "Quản lý nhiều dự án khách hàng, nhóm từ khóa, so sánh đối thủ và xuất báo cáo SEO trong cùng một tài khoản SERP SaaS dành cho người làm agency.",
  heading: "Theo dõi thứ hạng từ khóa cho SEO Agency",
  eyebrow: "Quy trình theo dõi cho khách hàng",
  lead: "Tổ chức dữ liệu theo từng khách hàng, đọc biến động trên cùng bộ từ khóa và chuẩn bị báo cáo có bối cảnh rõ ràng.",
  note: "Quản lý nhiều dự án khách hàng trong cùng một tài khoản. Các lần kiểm tra hiện tại bao phủ Top 10.",
  workflow: {
    heading: "Chuẩn bị một kỳ báo cáo khách hàng",
    steps: [
      "Thêm website khách hàng và tạo dự án theo môi trường tìm kiếm.",
      "Chia từ khóa theo dịch vụ, khu vực hoặc chiến dịch.",
      "Đọc biến động và so sánh các đối thủ đã chọn.",
      "Xem trước báo cáo rồi xuất CSV hoặc PDF để chia sẻ.",
    ],
  },
  sections: [
    {
      heading: "Tách rõ dữ liệu từng khách hàng",
      paragraphs: [
        "Đặt tên dự án theo khách hàng và thiết bị để dễ chọn đúng dữ liệu khi chạy kiểm tra hoặc tạo báo cáo. Mỗi dự án xác định quốc gia, ngôn ngữ, vị trí và thiết bị tìm kiếm.",
        "Quyền sở hữu dữ liệu thuộc về người dùng của tài khoản. Các dự án giúp chủ tài khoản tổ chức nhiều khách hàng; việc phối hợp công việc và chia sẻ tệp được thực hiện qua quy trình hiện có của agency.",
      ],
    },
    {
      heading: "Tổ chức bộ từ khóa theo câu hỏi của khách hàng",
      paragraphs: [
        "Dùng Groups cho dịch vụ hoặc địa phương, Tags cho chiến dịch và ưu tiên xử lý. Một bộ từ khóa rõ ràng giúp trả lời những câu hỏi như nhóm dịch vụ nào đang giảm hạng.",
        "Xem lại nhãn và chế độ khớp Tags trước khi xuất tệp. Duy trì cùng bộ từ khóa qua các kỳ báo cáo, đồng thời ghi nhận những thay đổi làm ảnh hưởng đến phép so sánh.",
      ],
    },
    {
      heading: "So sánh khách hàng với đối thủ",
      paragraphs: [
        "Chọn website chính và đối thủ để xem mức hiện diện trong cùng các lần kiểm tra đã lưu. Những từ khóa có đối thủ xuất hiện giúp định hướng việc nghiên cứu nội dung hoặc trang đích.",
        "Độ bao phủ chỉ phản ánh bộ dữ liệu đã kiểm tra, không ước tính traffic hay thị phần. Vắng mặt trong một lần kiểm tra Top 10 đầy đủ không cho biết thứ hạng chính xác phía sau; dữ liệu chưa đầy đủ cần được đọc riêng.",
      ],
    },
    {
      heading: "Chuẩn bị báo cáo trước khi gửi",
      paragraphs: [
        "Xem trước khoảng thời gian, website và bộ lọc rồi xuất báo cáo PDF hoặc CSV. Trình bày môi trường tìm kiếm, các URL thay đổi và giới hạn dữ liệu để khách hàng hiểu đúng kết quả.",
        "Báo cáo email định kỳ, nếu được cấu hình, gửi đến email đã xác minh của chính tài khoản. Bạn kiểm tra tệp rồi chuyển cho khách hàng qua kênh liên lạc đang dùng.",
      ],
    },
    {
      heading: "Mở rộng dự án theo hạn mức phù hợp",
      paragraphs: [
        "Theo dõi số dự án, từ khóa và lượt kiểm tra hàng tháng trong tài khoản. Lịch hàng ngày hoặc hàng tuần tùy theo gói dịch vụ; Desktop và Mobile có hạn mức và gói riêng.",
        "Xem Bảng giá hiện hành khi thêm khách hàng mới. Mở rộng bộ từ khóa khi những quan sát bổ sung phục vụ được câu hỏi báo cáo cụ thể, thay vì tăng số lượng chỉ để có nhiều dữ liệu.",
      ],
    },
  ],
  midCta: { ...start, heading: "Tạo dự án cho kỳ báo cáo tiếp theo" },
  finalCta: { ...start, heading: "Bắt đầu theo dõi từ khóa khách hàng" },
  guide: baselineGuide,
};

export const vietnameseLandingPages = [
  vietnameseRankTracker,
  vietnameseDailyTracker,
  vietnameseAgencyTracker,
];
