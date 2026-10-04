# CI/CD từ GitHub tới Cloud Run

Sau khi kết nối repo, push/merge vào `main` sẽ tự kiểm tra code, build production
image, push Artifact Registry và cập nhật các service hiện có. Không cần đóng gói
source/upload Cloud Shell cho mỗi tính năng nữa. Repo của dự án là
`haunguyen0603/serp-saas`, project `serp-saas`, region `asia-southeast1`.

Google hỗ trợ cả **Cloud Build** và **Developer Connect** trong màn hình Connect
Repo của Cloud Run. Với repo này, dùng **Developer Connect để kết nối GitHub** và
**Cloud Build trigger dùng YAML trong repo** để điều khiển build/deploy.
Xem [continuous deployment](https://docs.cloud.google.com/run/docs/continuous-deployment)
và [Developer Connect GitHub triggers](https://docs.cloud.google.com/build/docs/automating-builds/github/build-repos-from-github?generation=connect).

## 1. Pipeline của dự án

| Trigger | File cấu hình | Khi nào chạy | Kết quả |
| --- | --- | --- | --- |
| `serp-web-main` | `infrastructure/gcp/cloudbuild-frontend-cd.yaml` | Thay đổi `frontend/**`, Dockerfile frontend hoặc helper/config liên quan trên `main` | lint → sinh Next.js types → typecheck → test → build → push → cập nhật `serp-web` → HTTP smoke checks |
| `serp-backend-main` | `infrastructure/gcp/cloudbuild-backend-cd.yaml` | Thay đổi `backend/**`, Dockerfile backend hoặc helper/config liên quan trên `main` | lint/format/typecheck/unit test → build → push → migration thành công → cập nhật worker → API → `/health/db` |

Mỗi image dùng tag `$BUILD_ID` riêng, kể cả khi chạy lại cùng commit. Worker và API
dùng cùng một backend image. Build context là **repo root `.`**, Dockerfile ở
`infrastructure/docker/`, target `production`. Chỉ sửa tài liệu không chạy build.
Thay đổi cả frontend và backend sẽ chạy cả hai trigger độc lập.

Frontend dùng public URLs ở **build time**. Build Type Dockerfile mặc định trong
wizard không đủ để cung cấp các build args đã dùng ở dự án. Backend còn cần chờ
migration trước khi deploy; vì vậy dùng YAML bên trên, thay vì cấu hình build tự
sinh. Các YAML `cloudbuild-frontend.yaml` và `cloudbuild-backend.yaml` cũ vẫn dành
cho build thủ công.

Backend unit checks dùng dependency giả lập; các test có marker `integration`
chưa chạy trong pipeline này. Chạy integration/smoke tests với PostgreSQL/Redis
ở môi trường kiểm thử trước khi merge. HTTP smoke check sau deploy không thay thế
kiểm tra signup/email/login, ranking và reports bằng browser.

## 2. Đưa source lên GitHub

Cloud Build checkout source đã **commit và push**, không thấy thay đổi chưa commit
trong IDE. Kiểm tra `git status`, commit các thay đổi ứng dụng cần phát hành cùng
các file CI mới, rồi push nhánh feature và merge vào `main` khi sẵn sàng.

Không commit `.env`, `.env.cloud-run.yaml`, password, private key hoặc service
account key. `.gitignore`/`.dockerignore` hiện đã loại trừ env local. Secrets runtime
tiếp tục nằm trong Secret Manager. Kết nối GitHub không yêu cầu tải service account
key xuống máy.

Sau đó mở Cloud Shell, clone repo mới vào thư mục riêng (hoặc pull một checkout
Git sạch), rồi chạy:

```sh
git clone https://github.com/haunguyen0603/serp-saas.git ~/serp-saas-ci
cd ~/serp-saas-ci
export GCP_PROJECT_ID=serp-saas
export GCP_LOCATION=asia-southeast1
sh infrastructure/gcp/cloud-run-ci.sh plan
sh infrastructure/gcp/cloud-run-ci.sh prepare
```

Repo private cần đăng nhập GitHub theo cơ chế đang dùng trên Cloud Shell.
`prepare` cần các service `serp-web`, `serp-api`, `serp-worker` và job
`serp-db-migrate` đã được deploy thành công theo các runbook ban đầu.

Nếu nhận `No such file or directory`, kiểm tra `pwd` và
`ls infrastructure/gcp/cloud-run-ci.sh`. Chạy helper từ thư mục chứa repo, không
phải thư mục home `~`. Nếu file mới chỉ có trong workspace local và chưa được
commit/push, clone/pull sẽ chưa tải được nó.

### Upload helper mới nếu checkout Cloud Shell chưa có

Trên máy local:

```sh
python3 infrastructure/gcp/package-cloudshell.py --ci-guide
```

Upload `dist/serp-saas-cloudrun-ci.tar.gz` bằng Cloud Shell **More (⋮) → Upload**,
rồi chạy trên Cloud Shell:

```sh
cd ~
tar -xzf serp-saas-cloudrun-ci.tar.gz
cd ~/serp-saas-cloudshell
ls infrastructure/gcp/cloud-run-ci.sh
export GCP_PROJECT_ID=serp-saas
export GCP_LOCATION=asia-southeast1
sh infrastructure/gcp/cloud-run-ci.sh plan
sh infrastructure/gcp/cloud-run-ci.sh prepare
```

Gói bổ sung chứa các helper/YAML CI mới nhất và tài liệu, không chứa `.env` hoặc
secret. Nó giải nén vào `~/serp-saas-cloudshell`, cập nhật helper trong checkout cũ
nếu thư mục đã có. Setup CI chỉ cần helper và tài nguyên GCP hiện có; còn để trigger
build được, cần commit/push cả các YAML CD, `cloud-run-release.sh` và source ứng dụng
lên nhánh `main` của GitHub. Upload helper không thay thế bước push source lên GitHub.

Script tạo hai execution identities `serp-ci-web` và `serp-ci-backend`, cấp quyền
ghi Artifact Registry/log, đọc source qua Developer Connect, cập nhật đúng các
Cloud Run resource và actAs runtime identities tương ứng. Nó không cấp trực tiếp
quyền đọc Secret Manager cho CI. Runtime identities vẫn dùng các quyền hiện tại.
Operator chạy `prepare` phải có quyền bật API, tạo service account/bucket và cấp
IAM trên project, registry, service/job và service account.

Bucket private `serp-saas-ci-locks` chứa một khóa cho frontend và một cho backend;
không chứa dữ liệu ứng dụng. Việc tạo khóa dùng generation precondition để chống
hai release cùng loại deploy đồng thời. Quyền deploy dùng
[Cloud Run Developer và Service Account User](https://docs.cloud.google.com/run/docs/reference/iam/roles).

## 3. Kết nối GitHub một lần

Trong Google Cloud console, project `serp-saas`:

1. Mở **Developer Connect → Connections**, chọn region **asia-southeast1**.
2. Tạo connection GitHub, đặt tên ví dụ `serp-github`. Đăng nhập và cài/cho phép
   GitHub App Google yêu cầu; chọn quyền truy cập repo `haunguyen0603/serp-saas`.
3. Link repository đó vào connection; đợi connection/link sẵn sàng.
4. Sao chép resource name đầy đủ của **repository link**, có dạng:

   ```text
   projects/<project>/locations/<region>/connections/<connection-thuc-te>/gitRepositoryLinks/<link-thuc-te>
   ```

`serp-github` chỉ là tên ví dụ khi tạo mới. Nếu đã kết nối qua wizard Cloud Run,
connection có thể tên `connection-...` và nằm ở `europe-west1`. Dùng lại connection
đó được: trigger/build chạy tại region của connection, còn Cloud Run/Artifact
Registry tiếp tục ở `asia-southeast1`. Script tự lấy region của trigger từ resource
name. Không đổi `GCP_LOCATION` sang Belgium chỉ để dùng connection ở đó.

Trên Cloud Shell, chọn region thực tế của connection (xem trong Console):

```sh
export DEV_CONNECT_REGION=asia-southeast1
# Nếu connection đang ở Belgium, dùng dòng này thay cho Singapore:
# export DEV_CONNECT_REGION=europe-west1
gcloud developer-connect connections list \
  --project=serp-saas --location="$DEV_CONNECT_REGION" --format='table(name)'
```

Lấy tên connection từ kết quả, thay `TEN_CONNECTION_THUC_TE` bên dưới bằng ID hoặc
nguyên resource name của connection, rồi liệt kê repository links:

```sh
gcloud developer-connect connections git-repository-links list \
  --project=serp-saas --location="$DEV_CONNECT_REGION" \
  --connection=TEN_CONNECTION_THUC_TE \
  --format='value(name)'
```

Nếu nhận `NOT_FOUND`, kiểm tra project, region và tên connection. Địa chỉ
`https://europe-west1-git.developerconnect.dev/...` là URL clone/proxy, không phải
resource name. Không ghép URL đó vào sau `gitRepositoryLinks/` và không dùng tên
GitHub `haunguyen0603/serp-saas` để tự dựng link ID. Chỉ dùng dòng `name` trả về bởi
lệnh trên. Dòng đó có thể dùng project number thay project ID; giữ nguyên kết quả.

Ảnh bạn gửi là màn hình **Create service**. Với hệ thống đã deploy, dùng connection
ở trên và trigger bên dưới để cập nhật service hiện có. Không tạo thêm một frontend
service khác ở `europe-west1`. Nếu đã tạo trigger qua **Cloud Run → serp-web →
Connect repo / Set up continuous deployment**, disable trigger tự sinh đó trước
khi bật trigger YAML để tránh hai pipeline cùng deploy `serp-web`.

## 4. Tạo trigger với YAML của repo

Connection đã xác nhận cho project này nằm ở `europe-west1`, ID
`connection-bvmeqnc`, repository link `haunguyen0603-serp-saas`. Trên Cloud Shell:

```sh
export GIT_REPOSITORY_LINK='projects/serp-saas/locations/europe-west1/connections/connection-bvmeqnc/gitRepositoryLinks/haunguyen0603-serp-saas'
```

Nếu dùng connection khác, thay toàn bộ nội dung trong dấu nháy bằng resource name
đã lấy ở bước 3. Dấu nháy trong lệnh `export` là cú pháp shell, không thuộc giá trị.
Nếu trước đó dùng `read` và nhập cả dấu nháy, chạy lại lệnh `export` để sửa giá trị.

Kiểm tra giá trị bằng `printf '%s\n' "$GIT_REPOSITORY_LINK"`; nó phải bắt đầu bằng
`projects/` và có đúng một link ID sau `gitRepositoryLinks/`, không chứa `https://`.

Nếu HTTPS của ba domain đã hoạt động, dùng các origin production:

```sh
export FRONTEND_ORIGIN=https://serpsaas.com
export FRONTEND_APP_ORIGIN=https://app.serpsaas.com
export FRONTEND_API_URL=https://api.serpsaas.com
```

Nếu vẫn kiểm thử bằng `run.app`, dùng:

```sh
export FRONTEND_ORIGIN=https://serp-web-833917440392.asia-southeast1.run.app
export FRONTEND_APP_ORIGIN="$FRONTEND_ORIGIN"
export FRONTEND_API_URL=https://serp-api-833917440392.asia-southeast1.run.app
```

Các origin phải khớp frontend/API đang hoạt động, không có dấu `/` cuối URL.
Khi đổi domain, cập nhật CORS/`AUTH_SITE_URL` một lần theo runbook frontend bằng
`sh infrastructure/gcp/cloud-run-frontend.sh auth-origin`; pipeline không tự đổi
SMTP, secret, provider hoặc origin runtime backend.

```sh
sh infrastructure/gcp/cloud-run-ci.sh triggers
```

Script tạo hoặc cập nhật hai trigger, event **push to branch**, regex **`^main$`**,
region theo repository link, config **Cloud Build configuration file trong repo**, chọn
execution identity riêng và lọc các đường dẫn tương ứng. Nó gắn label
`gcb-trigger-id` để mở build/repo settings từ Cloud Run. Backend trigger được gắn
cho cả API và worker. Lệnh Developer Connect trigger hiện dùng nhóm
[`gcloud alpha builds triggers`](https://docs.cloud.google.com/sdk/gcloud/reference/alpha/builds/triggers/create/developer-connect).

Trong **Cloud Build → Triggers**, kiểm tra:

| Trường | Frontend | Backend |
| --- | --- | --- |
| Repository | `haunguyen0603/serp-saas` | Cùng repo |
| Branch | `^main$` | `^main$` |
| Trigger region | Cùng region với repository link | Cùng region với repository link |
| Config file | `infrastructure/gcp/cloudbuild-frontend-cd.yaml` | `infrastructure/gcp/cloudbuild-backend-cd.yaml` |
| Service account | `serp-ci-web@serp-saas.iam.gserviceaccount.com` | `serp-ci-backend@serp-saas.iam.gserviceaccount.com` |
| `_REGION` | `asia-southeast1` | `asia-southeast1` |
| `_REPOSITORY` | `serp-saas` | `serp-saas` |
| `_LOCK_BUCKET` | `serp-saas-ci-locks` | `serp-saas-ci-locks` |
| `_API_URL`, `_SITE_URL`, `_APP_URL` | Ba origin vừa chọn | Không dùng |

Chọn **Run** từng trigger với branch `main` cho lần đầu. Build này phát hành source
trên GitHub lên production. Chờ thành công, xem logs từng step và mở website/app.
Nếu thay đổi origin sau này, export lại các URL và chạy `triggers` để cập nhật
substitutions, rồi Run frontend trigger để compile bundle mới.

## 5. Quy trình cho các tính năng tiếp theo

Làm việc trên nhánh feature → kiểm thử → PR → merge `main` → trigger tương ứng tự
chạy. Push vào nhánh feature chưa deploy production. Pipeline hiện không tạo
preview environment và không gắn deploy trigger vào pull request.

Giữ thay đổi DB tương thích với phiên bản API/worker đang chạy vì migration xảy ra
trước cập nhật container. Frontend và backend deploy độc lập; khi thay đổi contract,
phát hành backend tương thích trước rồi mới phát hành frontend sử dụng contract mới.
Các migration xóa/đổi tên cột cần rollout nhiều bước và review dữ liệu trước merge.

`cloud-run-release.sh` chỉ đổi image rồi chuyển 100% traffic tới revision mới; các
runtime settings/Cloud SQL/secrets/IAM giữ cấu hình service hiện tại. Migration
lỗi thì chưa cập nhật worker/API. Deploy hoặc smoke check lỗi sau đó làm build thất
bại nhưng không tự rollback migration/container đã cập nhật; xem trạng thái cả hai
service trước khi chạy lại.

Hai build cùng loại đến bước release cùng lúc: một build giữ khóa, build còn lại
thất bại. Chờ build đang chạy xong rồi Run trigger với **commit mới nhất**. Khóa
chống chạy đồng thời, không tự xếp commit theo thứ tự; cancel build cũ chưa release
khi đã có commit mới và không Run lại commit cũ để sửa lỗi của commit mới.

Nếu cancel/timeout làm khóa còn lại, xem build ID trong khóa và xác nhận không còn
release hoặc migration execution đang chạy trước khi gỡ khóa. Không chạy các helper
deploy/migration thủ công song song với CI vì chúng không sử dụng khóa này.

```sh
gcloud storage cat gs://serp-saas-ci-locks/backend.lock
gcloud builds list --project=serp-saas --region="$DEV_CONNECT_REGION" --ongoing
gcloud run jobs executions list --job=serp-db-migrate \
  --project=serp-saas --region=asia-southeast1
# Chỉ sau khi xác nhận execution/build đã dừng:
gcloud storage rm gs://serp-saas-ci-locks/backend.lock
```

Dùng `frontend.lock` tương tự nếu frontend bị kẹt. Để rollback code, chọn revision
tốt trước đó trong **Cloud Run → service → Revisions → Manage traffic**; với backend
cần kiểm tra cả API/worker và khả năng tương thích schema đã migrate. Cloud Build,
Artifact Registry và bucket khóa dùng tài nguyên có tính phí theo mức sử dụng.

Các file CI được chuẩn bị/kiểm tra ở workspace local; chưa kết nối GitHub, tạo IAM,
tạo trigger hoặc deploy trên project GCP từ workspace này.
