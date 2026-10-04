# Deploy API và worker lên Cloud Run

Hướng dẫn này tiếp nối migration Cloud SQL đã chạy thành công. Chạy các lệnh trên
Cloud Shell, trong `~/serp-saas-cloudshell`. API và worker dùng lại production image
của job `serp-db-migrate`; không cần build lại chỉ để bổ sung script vận hành.
Các script đã được kiểm tra bằng giả lập CLI ở máy local, chưa chạy deploy từ workspace này.

Sau khi hệ thống hoạt động, dùng [CI/CD từ GitHub](cloud-run-ci-cd.md) để tự build,
chờ migration thành công rồi cập nhật API/worker khi merge thay đổi vào `main`.

## 1. Đưa script mới lên Cloud Shell

Tạo lại gói bổ sung trên máy local khi cần bằng:

```sh
python3 infrastructure/gcp/package-cloudshell.py --runtime-guide
```

Nếu checkout Cloud Shell chưa có `infrastructure/gcp/cloud-run-services.sh`, upload
`dist/serp-saas-cloudrun-guide.tar.gz` từ máy local bằng **More (⋮) → Upload**, rồi chạy:

```sh
cd ~
tar -xzf serp-saas-cloudrun-guide.tar.gz
cd ~/serp-saas-cloudshell
ls infrastructure/gcp/cloud-run-services.sh
```

Gói bổ sung chỉ chứa script và tài liệu; không chứa `.env`, password hoặc dữ liệu
local. Nó cần checkout đầy đủ đã dùng cho migration. Nếu chưa có checkout đó, tạo
gói đầy đủ trên máy local bằng `python3 infrastructure/gcp/package-cloudshell.py`
và làm theo [hướng dẫn upload source](cloud-sql-deployment.md#1-open-an-authenticated-cloud-shell-checkout).

```sh
gcloud config set project serp-saas
export GCP_PROJECT_ID=serp-saas
export GCP_LOCATION=asia-southeast1
sh infrastructure/gcp/cloud-run-services.sh plan
```

## 2. Chuẩn bị quyền và tài nguyên runtime

```sh
sh infrastructure/gcp/cloud-run-services.sh prepare
```

Script bật API cần thiết, tạo tài nguyên còn thiếu và cấp quyền runtime:

| Tài nguyên                    | Tên / mục đích                                                                   |
| ----------------------------- | -------------------------------------------------------------------------------- |
| API runtime identity          | `serp-api@serp-saas.iam.gserviceaccount.com`                                     |
| Worker runtime identity       | `serp-worker@serp-saas.iam.gserviceaccount.com`                                  |
| Task invocation identity      | `serp-task-invoker@serp-saas.iam.gserviceaccount.com`                            |
| Scheduler invocation identity | `serp-scheduler-invoker@serp-saas.iam.gserviceaccount.com`                       |
| Cloud Tasks queue             | `rank-checks`, Singapore, tối đa 2 dispatch/giây và 2 đồng thời                  |
| GCS report bucket             | `serp-saas-reports-833917440392`, private                                        |
| Runtime secrets               | `serp-jwt-key`, `serp-serper-key`, `serp-serpapi-key`, `serp-auth-smtp-password` |

Hai runtime identity có Cloud SQL Client, quyền enqueue trên queue, quyền actAs
task identity, quyền đọc/ghi/xóa object trên bucket báo cáo và đọc năm secret cụ thể
(bao gồm `serp-database-url` đã tạo). Script không đổi password database và không
tạo lại phiên bản database secret. Quyền của Cloud Tasks/Scheduler service agent
do Google quản lý cần được giữ nguyên.

Tài khoản operator cần quyền tạo các tài nguyên trên, cấp IAM, deploy Cloud Run và
actAs các runtime/invocation identity. Đây là quyền quản trị của người deploy,
khác quyền ứng dụng. Nếu xuất hiện `PERMISSION_DENIED`, đọc identity và permission
trong lỗi rồi xử lý quyền tương ứng trước khi chạy lại bước đó.

## 3. Bổ sung JWT, SERP API key và SMTP password

Hướng dẫn chọn **Serper** làm SERP provider. Chuẩn bị Serper API key hợp lệ và một
dịch vụ SMTP với host, port TLS 587 hoặc 465, username, password và địa chỉ gửi đã
được nhà cung cấp cho phép. Nếu chưa có SMTP, có thể hoàn tất bước 2 và JWT/Serper
bên dưới trước; cần có SMTP thật để tiếp tục bước cấu hình và deploy.

```sh
python3 infrastructure/gcp/create-runtime-secret.py serp-jwt-key --generate-jwt
python3 infrastructure/gcp/create-runtime-secret.py serp-serper-key
python3 infrastructure/gcp/create-runtime-secret.py serp-auth-smtp-password
```

JWT được sinh ngẫu nhiên. Hai lệnh còn lại hỏi giá trị bằng prompt ẩn, gửi qua stdin
đến Secret Manager, không đưa password/API key vào shell history. Mỗi lần chạy tạo
**một phiên bản mới**. Ghi lại số phiên bản cuối output; không chạy lại JWT chỉ để
xem giá trị vì đổi JWT sẽ ảnh hưởng phiên đăng nhập.

Nếu đây là phiên bản đầu của ba secret mới, và database vẫn dùng phiên bản 1:

```sh
export DATABASE_SECRET_VERSION=1
export JWT_SECRET_VERSION=1
export SERPER_SECRET_VERSION=1
export SMTP_SECRET_VERSION=1
```

Thay số bằng phiên bản thực tế nếu khác. Các deployment pin phiên bản số, không dùng `latest`.

### Bổ sung SerpAPI key bên cạnh Serper

Upload lại gói `serp-saas-cloudrun-guide.tar.gz` mới và giải nén theo bước 1 để
cập nhật script. Trong checkout Cloud Shell, chạy:

```sh
sh infrastructure/gcp/cloud-run-services.sh prepare
python3 infrastructure/gcp/create-runtime-secret.py serp-serpapi-key
export SERPAPI_SECRET_VERSION=1
```

Nhập SerpAPI key ở prompt ẩn và dùng đúng số phiên bản được trả về, thay `1` nếu
khác. `prepare` tạo secret còn thiếu và cấp Secret Accessor cho cả API/worker;
không tạo thêm phiên bản cho các secret đã có. Khi biến `SERPAPI_SECRET_VERSION`
được đặt, bước deploy kiểm tra phiên bản đó là số và đang enabled, rồi inject
`SERPAPI_API_KEY=serp-serpapi-key:<version>` vào cả hai service.

Nếu gặp `invalid choice: 'serp-serpapi-key'`, checkout Cloud Shell vẫn đang dùng
script cũ. Kiểm tra bằng `python3 infrastructure/gcp/create-runtime-secret.py --help`:
phải thấy `serp-serpapi-key` trong danh sách lựa chọn. Upload lại gói mới từ workspace
local và giải nén đúng file vừa upload; Cloud Shell có thể giữ nhiều file cùng tên
khi upload lại. Dùng `ls -lt ~/serp-saas-cloudrun*.tar.gz` để tìm tên file thực tế.
Sau khi cập nhật, chạy lại `prepare` rồi lệnh thêm SerpAPI key. Lỗi argparse này xảy
ra trước khi gọi Secret Manager, nên chưa tạo phiên bản SerpAPI secret và không cần
tạo lại JWT/Serper/SMTP secrets.

Nếu đã deploy, giữ nguyên `.env.cloud-run.yaml`, các biến phiên bản secret khác
và image của lần deploy hiện tại; chạy lại:

```sh
sh infrastructure/gcp/cloud-run-services.sh worker
sh infrastructure/gcp/cloud-run-services.sh api
sh infrastructure/gcp/cloud-run-services.sh verify
```

Nếu chưa deploy, tiếp tục bước 4 trở đi. Trong mỗi session Cloud Shell mới, export
lại `SERPAPI_SECRET_VERSION` trước khi deploy để giữ binding SerpAPI, vì script dùng
`--set-secrets` để thay toàn bộ danh sách binding. Không cần build lại image hoặc
chạy lại migration chỉ để thêm key.

Việc inject key không đổi provider đang dùng: profile mặc định vẫn chọn cố định
Serper. Để bật cả hai với thứ tự Serper trước, SerpAPI sau, chỉnh các giá trị sau
trong `.env.cloud-run.yaml`, rồi redeploy cả hai service:

```json
{
  "SERP_ENABLED_PROVIDERS": "serper,serpapi",
  "SERP_PROVIDER_STRATEGY": "priority",
  "SERP_PROVIDER_PRIORITY": "serper,serpapi"
}
```

Chỉ sửa ba field này trong profile hiện có; không thay cả file bằng đoạn JSON trên.
Nếu chạy lại bước `config`, các field provider sẽ trở về mặc định Serper.

## 4. Tạo cấu hình production

```sh
sh infrastructure/gcp/cloud-run-services.sh config
```

Nhập SMTP host, port, sender và username thật khi được hỏi. Script tạo
`.env.cloud-run.yaml` tại root checkout; password và API key được inject riêng từ
Secret Manager. Không upload `.env` local lên Cloud Run.

Vì chưa có domain, script mặc định frontend dự kiến là:

```text
https://serp-web-833917440392.asia-southeast1.run.app
```

Đây là URL dự kiến cho service frontend tên `serp-web`; frontend **chưa được deploy**
bởi hướng dẫn này. Email xác minh trỏ về URL đó, nên chưa mở được trang xác minh
cho đến khi frontend được deploy. Cloud Run hỗ trợ URL xác định trước theo tên
service/project number/region; xem [tài liệu URL Cloud Run](https://docs.cloud.google.com/run/docs/triggering/https-request#deterministic_url).

Nếu sau này frontend ở URL khác, chạy lại bước cấu hình với origin HTTPS thực tế,
không có dấu `/` cuối, rồi redeploy **cả API và worker**:

```sh
export FRONTEND_ORIGIN=https://your-actual-frontend.example
sh infrastructure/gcp/cloud-run-services.sh config
```

`AUTH_SITE_URL` và CORS cùng dùng origin này. Profile dùng Secure cookie và
`SameSite=None` vì các origin `run.app` khác nhau; cần kiểm tra đăng nhập/refresh
trên trình duyệt sau khi deploy frontend. Trình duyệt có thể chặn cookie bên thứ
ba; domain cùng site hoặc proxy API qua frontend là hướng cấu hình khi go-live.

Redis hiện chỉ phục vụ `/health/redis`, không phải queue ranking. Profile mặc định
giữ `REDIS_URL=redis://127.0.0.1:6379/0` để đáp ứng setting bắt buộc; không có Redis
local trong container Cloud Run nên endpoint đó sẽ lỗi. Dùng `/health` và
`/health/db` để kiểm tra deployment này. Nếu cần Redis health, truyền endpoint
Redis truy cập được qua biến `REDIS_URL` khi tạo profile.

## 5. Deploy worker và cấp quyền gọi

```sh
sh infrastructure/gcp/cloud-run-services.sh worker
sh infrastructure/gcp/cloud-run-services.sh worker-iam
```

Script lấy image từ job `serp-db-migrate`. Có thể chỉ định `BACKEND_IMAGE` nếu cần
dùng đúng image production đã được kiểm tra và migration; không dùng tag local/dev.
Worker chạy `uvicorn app.worker_main:app` tại port 8080, generation 2, gắn Cloud SQL
`serp-saas:asia-southeast1:serp-saas`, concurrency 1, CPU 1, RAM 512 MiB,
min instances 0, max instances 2 và timeout 300 giây.

Worker yêu cầu IAM, chỉ cấp Run Invoker cho task và Scheduler identities. URL:

```text
https://serp-worker-833917440392.asia-southeast1.run.app
```

Ứng dụng còn kiểm tra OIDC audience và email service account trên route internal.
Token phải ở header `Authorization`; không đổi sang `X-Serverless-Authorization`
vì Cloud Run loại bỏ chữ ký ở header đó trước khi chuyển vào container, trong khi
worker cần xác minh chữ ký. Xem [xác thực service-to-service](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

## 6. Deploy API

```sh
sh infrastructure/gcp/cloud-run-services.sh api
```

API chạy `python -m app`, port 8080, generation 2, cùng Cloud SQL và các secret đã
pin; CPU 1, RAM 512 MiB, concurrency 8, min instances 0, max instances 2. Endpoint
công khai cho frontend; các business route vẫn yêu cầu xác thực của ứng dụng.

API dùng `--no-cpu-throttling` để xử lý SMTP BackgroundTask sau response. Đây là
instance-based billing, CPU vẫn được cấp ngoài thời gian request, nên instance
đang tồn tại có thể phát sinh phí khi idle. Min instances 0 vẫn cho phép scale về 0. Xem [billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings).
Email hiện chưa có durable outbox; nếu instance bị ngắt trước khi gửi xong, user
cần dùng chức năng resend verification.

URL API:

```text
https://serp-api-833917440392.asia-southeast1.run.app
```

## 7. Tạo lịch dispatch

```sh
sh infrastructure/gcp/cloud-run-services.sh scheduler
```

Job `rank-schedule-dispatch` chạy mỗi 5 phút UTC, POST
`/internal/schedules/dispatch` với Scheduler identity và OIDC audience là worker
origin. Endpoint dispatch/recovery phục vụ cả ranking và report. Script cập nhật
job cùng tên nếu đã có. Xem [Scheduler HTTP authentication](https://docs.cloud.google.com/scheduler/docs/http-target-auth).

## 8. Kiểm tra deployment

```sh
sh infrastructure/gcp/cloud-run-services.sh verify
```

Kết quả cần có: hai service Ready, API `/health` và `/health/db` trả `status: ok`,
worker chặn truy cập anonymous bằng HTTP 401/403. Worker mở trực tiếp trong browser
bị 403 là hành vi mong đợi.

Kiểm tra thêm kết nối database từ worker bằng token của operator có Run Invoker
(token chỉ dùng kiểm tra health; không thay task/Scheduler identity trên internal route):

```sh
curl --fail --show-error \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://serp-worker-833917440392.asia-southeast1.run.app/health/db
```

Sau đó kích hoạt Scheduler một lần và kiểm tra Logs của worker:

```sh
gcloud scheduler jobs run rank-schedule-dispatch \
  --project=serp-saas --location=asia-southeast1
gcloud run services logs read serp-worker \
  --project=serp-saas --region=asia-southeast1 --limit=30
```

Việc `jobs run` thành công chỉ xác nhận yêu cầu chạy được nhận; cần thấy POST dispatch
HTTP 200 trong worker logs/Scheduler execution logs. Database mới có thể trả số
dispatch bằng 0. Với dữ liệu thật, lệnh này có thể enqueue công việc đã đến hạn.
Health checks chưa chứng minh Serper key, SMTP hoặc GCS upload hoạt động thực tế.
Sau khi có frontend, kiểm tra signup → nhận email → verify → login → rank check
hoàn tất → xuất report để xác nhận toàn bộ luồng.
Tiếp tục với [deploy frontend và kiểm tra website](cloud-run-frontend-deployment.md).

Nếu service không Ready, đọc startup logs của service tương ứng:

```sh
gcloud run services logs read serp-api \
  --project=serp-saas --region=asia-southeast1 --limit=50
```

Các lỗi thường gặp: secret thiếu/disabled, quyền Secret Accessor hoặc Cloud SQL
Client chưa có, password database sai, hoặc SMTP/provider settings không hợp lệ.
Không gửi nội dung secret khi chia sẻ lỗi.

## Kiểm tra local cho helper

Shell syntax và Python lint đã được kiểm tra. Các phase đã chạy với `gcloud`/`curl`
giả lập: tạo mới và chạy lại hạ tầng, deploy API/worker, IAM worker, tạo/cập nhật
Scheduler, health, pin secret và chặn profile sai project. Profile SMTP 587/465 đã
được kiểm tra về các biến cấu hình và TLS, dùng credential giả chỉ trong test.
Không có tài nguyên GCP nào được tạo bởi các kiểm tra local này.
