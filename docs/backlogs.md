# Limitation in Milestone 2
1.
logout chỉ revoke refresh token. Access JWT đã phát hành vẫn có thể hoạt động tối đa 15 phút, trừ khi user bị disabled.

Điều này hoàn toàn chấp nhận được cho MVP. Tôi không khuyên thêm JWT deny-list ngay bây giờ, vì sẽ làm auth phụ thuộc Redis/database trên mỗi request và tăng complexity.

2.
refresh single-flight hiện chỉ phối hợp trong cùng một mounted browser app. Hai tab refresh đồng thời có thể khiến một tab mất session.

Cũng chưa cần sửa ngay. Khi app thực tế có nhiều người dùng, chúng ta có thể cân nhắc cross-tab coordination bằng BroadcastChannel.
