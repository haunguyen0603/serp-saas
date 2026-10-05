# Deploy frontend sau API và worker

Chạy trên Cloud Shell trong checkout đầy đủ `~/serp-saas-cloudshell`. API, worker,
database và Scheduler đã được deploy theo [runbook backend](cloud-run-deployment.md).
Hướng dẫn này tạo service Next.js `serp-web`, nối frontend với API và kiểm tra luồng
thực tế. Chưa có lệnh GCP nào được chạy từ workspace local cho bước này.

Sau lần deploy đầu, dùng [CI/CD qua Connect Repo](cloud-run-ci-cd.md) để tự kiểm tra,
build và deploy khi merge vào `main`, thay cho upload source ở mỗi lần cập nhật.

## 1. Kiểm tra backend và Scheduler

```sh
cd ~/serp-saas-cloudshell
sh infrastructure/gcp/cloud-run-services.sh verify
gcloud scheduler jobs run rank-schedule-dispatch \
  --project=serp-saas --location=asia-southeast1
gcloud run services logs read serp-worker \
  --project=serp-saas --region=asia-southeast1 --limit=30
```

Cần thấy API `/health/db` trả `status: ok`, worker chặn anonymous và POST Scheduler
dispatch trả HTTP 200 trong execution logs. Lệnh `jobs run` nhận yêu cầu thành công
chưa chứng minh dispatch đã thành công; chờ execution và kiểm tra logs. Database
mới có thể chưa có công việc đến hạn; việc dispatch bằng 0 là bình thường.

## 2. Upload helper frontend

Gói bổ sung được tạo trên máy local bằng:

```sh
python3 infrastructure/gcp/package-cloudshell.py --frontend-guide
```

Upload `dist/serp-saas-cloudrun-frontend.tar.gz` bằng **More (⋮) → Upload**, rồi chạy
trên Cloud Shell:

```sh
cd ~
tar -xzf serp-saas-cloudrun-frontend.tar.gz
cd ~/serp-saas-cloudshell
sh infrastructure/gcp/cloud-run-frontend.sh plan
```

Gói này chỉ bổ sung script/tài liệu vào checkout hiện có, không chứa `.env` hoặc
secret. Nó không chứa toàn bộ frontend source; checkout từ migration ban đầu phải
có `frontend/` và `infrastructure/docker/frontend.Dockerfile`. Dùng gói source đầy
đủ từ [hướng dẫn Cloud SQL](cloud-sql-deployment.md) nếu thiếu các file đó.

## 3. Build production image

Trước tiên dùng URL `run.app` để kiểm tra triển khai. Khi domain riêng đã được
cấu hình HTTPS, làm theo bước domain bên dưới và build lại với URL thực tế.

```sh
export GCP_PROJECT_ID=serp-saas
export GCP_LOCATION=asia-southeast1
unset FRONTEND_ORIGIN FRONTEND_APP_ORIGIN FRONTEND_API_URL
export FRONTEND_IMAGE_TAG="web-$(date -u +%Y%m%d-%H%M%S)"
sh infrastructure/gcp/cloud-run-frontend.sh build
```

Script lấy URL API từ service `serp-api`, dùng site origin dự kiến
`https://serp-web-833917440392.asia-southeast1.run.app` và build production target của
Dockerfile frontend trên Cloud Build. Image được push vào repository Artifact
Registry đã dùng cho backend. Build dùng execution identity/quyền đã chuẩn bị cho
backend; nếu gặp source-read 403, xem bước `build-access` trong runbook Cloud SQL.

Các public build arguments là `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV`,
`NEXT_PUBLIC_SITE_URL` và `NEXT_PUBLIC_APP_URL`. Không đưa JWT, database URL, SMTP password hoặc SERP key
vào chúng. Next.js compile public environment variables vào browser bundle;
thay đổi URL cần build lại image, không chỉ đổi Cloud Run runtime environment.
Xem [Next.js environment variables](https://nextjs.org/docs/app/guides/environment-variables).

Giữ nguyên `FRONTEND_IMAGE_TAG` để deploy đúng image vừa build. Nếu mở session mới,
export lại đúng tag đã dùng. Chỉ deploy khi build đã thành công.

## 4. Deploy frontend và cập nhật email/CORS

```sh
sh infrastructure/gcp/cloud-run-frontend.sh deploy
sh infrastructure/gcp/cloud-run-frontend.sh auth-origin
sh infrastructure/gcp/cloud-run-frontend.sh verify
```

Frontend có runtime identity riêng `serp-web` không có quyền đọc secret backend,
chạy Node standalone server port 3000, CPU 1, RAM 512 MiB, concurrency 20,
min instances 0, max instances 2, public endpoint. Operator cần quyền tạo service
account và actAs identity này. Ứng dụng frontend gọi API từ browser bằng public
URL đã compile khi build.

`auth-origin` đặt `AUTH_SITE_URL` theo application origin, cho phép CORS từ cả
website và application origin, đồng thời đồng bộ hai field đó trong `.env.cloud-run.yaml` nếu file tồn tại. Các binding
secret và SMTP/provider settings của service được giữ nguyên, không cần tạo lại
JWT hoặc password. URL kiểm tra:

```text
https://serp-web-833917440392.asia-southeast1.run.app
```

## 5. Kiểm tra bằng browser

1. Mở website; kiểm tra Home, Pricing, About, Privacy và Terms.
2. Đăng ký một tài khoản mới bằng email bạn nhận được mail.
3. Nhận email xác minh; link phải trỏ về frontend vừa deploy. Dùng resend nếu email
   trước đó trỏ về URL cũ.
4. Xác minh rồi login; reload `/app`, logout và login lại để kiểm tra refresh cookie.
5. Tạo Tracked Site, Project và vài Keyword; Check Rankings phải chuyển sang completed.
6. Xuất report và download để kiểm tra worker/GCS.

Nếu không nhận được email xác minh, làm theo
[chẩn đoán email trên Cloud Run](email-verification.md#cloud-run-missing-verification-email)
để kiểm tra SMTP settings, password binding, CPU và log gửi mail.

Các origin `run.app` khác nhau có thể bị browser chặn third-party cookies dù API
đã đặt Secure và SameSite=None. Nếu login/reload không giữ phiên, kiểm tra cookie
và Network tab rồi chuyển sang frontend/API subdomain cùng site như bước 6. Không
dùng việc trang Home mở được làm bằng chứng toàn bộ luồng đăng nhập hoạt động.

Nếu dùng Mobile, bật SerpAPI trong provider configuration của cả API và worker;
registry hiện giới hạn Serper ở Desktop. Việc thêm SerpAPI secret riêng chưa bật
provider. Cách cấu hình cả hai được ghi trong runbook backend.

### Login báo “The service is unavailable” sau khi đổi domain

Kiểm tra DevTools → Network → request `login`: lấy Request URL, Status và Response,
không chia sẻ payload/password, token hoặc cookie. API URL nằm trong frontend bundle
đã build; việc đổi domain website hoặc runtime env không tự thay đổi URL này.

Nếu API `/health/db` trả 200 nhưng preflight OPTIONS trả 400 với nội dung
`Disallowed CORS origin`, API chưa cho phép origin của trang đăng nhập. Đây là lỗi
cấu hình origin; chưa cần thay đổi mật khẩu hoặc build lại backend.
Xem [CORS trong FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).

Ví dụ khôi phục login khi mới có `https://serpsaas.com` hoạt động, frontend vẫn
gọi API `run.app`, còn DNS/HTTPS của `app` và `api` chưa sẵn sàng. Trong thư mục
checkout Cloud Shell đang dùng, export **cả ba biến** rồi cập nhật:

```sh
export GCP_PROJECT_ID=serp-saas
export GCP_LOCATION=asia-southeast1
export FRONTEND_ORIGIN=https://serpsaas.com
export FRONTEND_APP_ORIGIN=https://serpsaas.com
export FRONTEND_API_URL=https://serp-api-833917440392.asia-southeast1.run.app
sh infrastructure/gcp/cloud-run-frontend.sh auth-origin
```

Đây là cấu hình tạm cho login/verification trên domain chính. Nó đặt
`AUTH_SITE_URL=https://serpsaas.com` và `CORS_ORIGINS=["https://serpsaas.com"]`, đồng
thời đồng bộ profile local nếu có. Chạy `auth-origin` trong shell mới mà chưa export
origin sẽ dùng mặc định `run.app`; script không tự đọc các biến từ `.env` của IDE.
Pipeline CI/CD đổi image nhưng giữ nguyên origin runtime API, nên chạy lại build
frontend cũng không tự sửa CORS.

Kiểm tra lại sau khi revision mới sẵn sàng:

```sh
curl --silent --show-error --include --max-time 20 \
  --request OPTIONS "$FRONTEND_API_URL/api/v1/auth/login" \
  --header "Origin: $FRONTEND_APP_ORIGIN" \
  --header 'Access-Control-Request-Method: POST' \
  --header 'Access-Control-Request-Headers: content-type'
```

Cần HTTP 200, `Access-Control-Allow-Origin: https://serpsaas.com` và
`Access-Control-Allow-Credentials: true`. Sau đó reload trang và thử login một lần.
Nếu frontend còn gọi một API URL khác, dùng đúng Request URL từ browser để kiểm tra.
Nếu API trả 500/503 hoặc không phân giải được DNS, cần xử lý lỗi đó riêng thay vì
chỉ cập nhật CORS.

Khi DNS/HTTPS của `app.serpsaas.com` và `api.serpsaas.com` đã hoạt động, hoàn tất
bước 6 để đưa luồng tài khoản sang app domain và API sang cùng site. Với CI/CD,
cập nhật substitutions của frontend trigger và chạy lại trigger như runbook CI/CD;
vẫn cần chạy `auth-origin` với ba origin mới. Kiểm tra cả login và reload để xác
nhận refresh cookie hoạt động sau khi chuyển domain.

## 6. Tách website thương mại và ứng dụng theo domain

Cấu hình production dùng ba hostname:

| Hostname           | Nội dung                                                   | Cloud Run backend |
| ------------------ | ---------------------------------------------------------- | ----------------- |
| `serpsaas.com`     | Home, Pricing, Terms, Privacy, About us                    | `serp-web`        |
| `app.serpsaas.com` | Register, Login, Verify email, workspace, billing và admin | `serp-web`        |
| `api.serpsaas.com` | API cho browser                                            | `serp-api`        |

Hai hostname frontend dùng chung service/image Next.js. `NEXT_PUBLIC_SITE_URL`
định nghĩa origin thương mại và canonical/sitemap; `NEXT_PUBLIC_APP_URL` định nghĩa
origin tài khoản/sản phẩm. Khi application origin không được cấu hình, nó dùng
site origin để giữ luồng localhost hoặc thử nghiệm `run.app` như trước.

Next.js Proxy chuyển hướng HTTP 307 theo Host header: các route `/login`,
`/register`, `/signup`, `/verify-email`, `/app/*`, `/settings/*`, `/admin/*` trên
domain chính sang app domain; `/pricing`, `/terms`, `/privacy`, `/about` trên app
sang domain chính. Root `app.serpsaas.com/` chuyển tới `/app`, nơi authentication
và email verification gate hiện tại tiếp tục xử lý. Người chưa đăng nhập sẽ tới
`/login`; người chưa xác minh email sẽ tới `/verify-email`. Home trên domain chính
vẫn mở được khi người dùng đã đăng nhập vào app. Proxy không thay thế kiểm tra
quyền ở frontend/API. Xem [Next.js Proxy](https://nextjs.org/docs/app/api-reference/file-conventions/proxy).

CTA trên Home/About/Pricing và header/footer chuyển sang app domain. Link Terms
và Privacy ở form đăng ký mở domain chính trong tab riêng. Website thương mại
không tự gọi refresh session khi hai domain được tách; các lần khôi phục phiên
và token giữ trong app. Refresh cookie vẫn là HttpOnly, Secure, thuộc API host;
không cần chia sẻ cookie bằng `Domain=.serpsaas.com`. API cho phép CORS từ cả hai
origin vì Pricing trên website thương mại cần đọc catalog công khai.

Sitemap chỉ chứa năm trang thương mại. App domain trả robots `Disallow: /` và
header `X-Robots-Tag: noindex, nofollow` cho các trang của nó. Auth pages có metadata
noindex. Không bật Cloud CDN/cache response cho các trang tài khoản hoặc API.

### 6.1 Tạo HTTPS Load Balancer

Google đề xuất global external Application Load Balancer để nối custom domain
Cloud Run trong production; domain mapping trực tiếp vẫn ở Preview. Load balancer
là tài nguyên riêng có tính phí. Xem [custom domains](https://docs.cloud.google.com/run/docs/mapping-custom-domains).

Trong project `serp-saas` trên Google Cloud console:

1. **Network services → Load balancing → Create load balancer**. Chọn
   **Application Load Balancer (HTTP/HTTPS)**, **Public-facing**, **Global**, và
   loại **Global external Application Load Balancer**. Đặt tên `serp-public-lb`.
2. Tạo frontend **HTTPS**, port `443`, và reserve một **global static external
   IPv4** tên `serp-public-ip`. Ghi lại IP Google cấp.
3. Tạo **Google-managed certificate** `serp-public-cert` bao gồm ba tên miền
   `serpsaas.com`, `app.serpsaas.com`, `api.serpsaas.com`; gắn certificate đó vào
   HTTPS frontend. Khi chưa trỏ DNS, certificate có thể ở trạng thái provisioning.
4. Tạo backend service `serp-web-backend`, loại **Serverless network endpoint
   group**, NEG `serp-web-neg`, region `asia-southeast1`, service `serp-web`.
   Tạo backend service `serp-api-backend`, NEG `serp-api-neg`, cùng region, service
   `serp-api`. Serverless NEG không dùng health check thông thường.
5. Đặt routing rules: host `serpsaas.com` và `app.serpsaas.com` cùng đi tới
   `serp-web-backend`; host `api.serpsaas.com` đi tới `serp-api-backend`, toàn bộ
   đường dẫn. Default backend có thể là `serp-web-backend`. Giữ nguyên Host header
   khi chuyển tới frontend; không cấu hình host rewrite giữa hai domain.
6. Bật **HTTP to HTTPS redirect** cho frontend, rồi tạo load balancer. Nếu đã có
   load balancer, bổ sung host/certificate vào cấu hình hiện tại thay vì tạo bản
   trùng. Không bật CDN cho backend app/API.

Theo [hướng dẫn load balancer với Cloud Run](https://docs.cloud.google.com/load-balancing/docs/https/setup-global-ext-https-serverless).
Tên menu có thể thay đổi; dùng IP/DNS values được tạo trong project của bạn.
Cloud Run không cung cấp IP service cố định để tự gán A record; IP Cloud SQL
hoặc IP email hosting không phải IP load balancer.

### 6.2 Cập nhật DNS của domain

Tại nhà cung cấp DNS authoritative (nơi nameserver của domain trỏ tới), tạo hoặc
cập nhật ba bản ghi, TTL ví dụ `300`:

| Type | Name  | Value                     |
| ---- | ----- | ------------------------- |
| A    | `@`   | IPv4 của `serp-public-ip` |
| A    | `app` | Cùng IPv4 load balancer   |
| A    | `api` | Cùng IPv4 load balancer   |

Loại bỏ A/AAAA/CNAME xung đột **chỉ ở ba hostname website này**. Nếu có AAAA, nó
phải trỏ tới IPv6 frontend đã cấu hình cho load balancer; nếu chưa có IPv6 frontend
thì bỏ AAAA của các hostname đó để DNS/certificate không dùng địa chỉ cũ.
Nếu dùng Cloudflare, để **DNS only** trong bước cấp chứng chỉ này.

Giữ MX, mail hostname, SPF/TXT, DKIM và DMARC của email hosting. Trước khi đổi A
của root, kiểm tra MX và hostname SMTP/IMAP: nếu chúng đang dùng chính
`serpsaas.com` làm mail server hoặc alias về root, yêu cầu nhà cung cấp chuyển
sang hostname email riêng để đổi website không đổi IP mail. Không đổi nameserver
nếu chưa chuyển đủ các bản ghi email. Với SPF đang dùng cơ chế `a`, xác nhận với
email hosting cách khai báo IP/include của máy chủ gửi khi IP root thay đổi.

Chờ DNS trỏ đúng IP và certificate **ACTIVE**, rồi kiểm tra HTTPS của cả ba host.
Chưa có domain nào được provision từ workspace local.

### 6.3 Upload source mới, build và cập nhật origin

Thay đổi routing nằm trong frontend source. Gói `--frontend-guide` chỉ có helpers
và tài liệu, không đủ để cập nhật source của checkout cũ. Trên máy local, tạo gói
đầy đủ bằng `python3 infrastructure/gcp/package-cloudshell.py --domains`, upload
`dist/serp-saas-domains.tar.gz` bằng Cloud Shell **More → Upload**, rồi chạy:

```sh
cd ~
tar -xzf serp-saas-domains.tar.gz
cd ~/serp-saas-cloudshell

export GCP_PROJECT_ID=serp-saas
export GCP_LOCATION=asia-southeast1
export FRONTEND_ORIGIN=https://serpsaas.com
export FRONTEND_APP_ORIGIN=https://app.serpsaas.com
export FRONTEND_API_URL=https://api.serpsaas.com
export FRONTEND_IMAGE_TAG="web-domains-$(date -u +%Y%m%d-%H%M%S)"

sh infrastructure/gcp/cloud-run-frontend.sh build
sh infrastructure/gcp/cloud-run-frontend.sh deploy
sh infrastructure/gcp/cloud-run-frontend.sh auth-origin
sh infrastructure/gcp/cloud-run-frontend.sh verify
```

Build phải thành công trước deploy. `auth-origin` cập nhật riêng:

```text
AUTH_SITE_URL=https://app.serpsaas.com
CORS_ORIGINS=["https://serpsaas.com","https://app.serpsaas.com"]
```

SMTP, JWT, database và provider secret bindings giữ nguyên. Không cần migration
hoặc redeploy worker cho thay đổi domain. Nếu deploy lại backend, dùng profile
`.env.cloud-run.yaml` đã đồng bộ để không đưa AUTH_SITE_URL/CORS về URL cũ. Các biến
`FRONTEND_ORIGIN` và `FRONTEND_APP_ORIGIN` cũng được hỗ trợ khi tạo lại profile.

### 6.4 Kiểm tra luồng trên domain

1. Mở `https://serpsaas.com`: Home và link Pricing/About/Terms/Privacy thuộc domain
   chính. Nút **Get Started / Start Free** mở `https://app.serpsaas.com/register`;
   **Log in** mở `https://app.serpsaas.com/login`.
2. Truy cập `https://serpsaas.com/app` hoặc `/login`: phải chuyển sang app domain,
   giữ nguyên path và query. Mở `https://app.serpsaas.com/pricing`: về domain chính.
3. Mở `https://app.serpsaas.com/`: tới `/app`; chưa login thì được chuyển tới
   `/login`. Đăng ký/login thành công nhưng chưa verify thì tới `/verify-email`.
   Verify xong mới dùng workspace.
4. Khi email hosting đã mở chặn MagicSpam, bấm Resend trên tài khoản hiện có.
   Link mới phải bắt đầu `https://app.serpsaas.com/verify-email#token=...`.
   Việc đổi domain không tự sửa hạn mức gửi email của nhà cung cấp.
5. Xác minh, login, reload trang sản phẩm, logout/login và thử rank check/report.
   Mở Home/Pricing trong tab khác không thay đổi trang hiện tại của workspace.
6. Kiểm tra `/sitemap.xml` trên domain chính có đúng năm trang thương mại;
   `https://app.serpsaas.com/robots.txt` trả `Disallow: /`.

Worker/Scheduler vẫn dùng URL IAM riêng đã có; không cần domain công khai cho worker.

## Điều kiện kiểm tra cuối

Trước mở đăng ký cho khách: signup/verify/login/refresh, rank check và report phải
pass trên domain; DNS gửi mail phải hợp lệ và email phải tới hộp thư thực tế.
Bổ sung tên đơn vị vận hành/email liên hệ còn thiếu trên Privacy/About, kiểm tra
backup Cloud SQL và đặt monitoring/budget phù hợp với lượng sử dụng dự kiến.
