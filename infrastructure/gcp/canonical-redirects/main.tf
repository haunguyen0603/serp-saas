# This state owns only the commercial-domain load balancer. Existing Cloud Run
# services, domain mappings, app/API DNS and IAM are deliberately outside it.
variable "enable_load_balancer" {
  description = "Enable only after the DNS-authorized certificate is ACTIVE."
  type        = bool
  default     = false
}

locals {
  prefix  = "serp-canonical"
  domains = { apex = "serpsaas.com", www = "www.serpsaas.com" }
}

resource "google_project_service" "required" {
  for_each           = toset(["compute.googleapis.com", "certificatemanager.googleapis.com"])
  project            = "serp-saas"
  service            = each.key
  disable_on_destroy = false
}

resource "google_compute_global_address" "web" {
  name         = "${local.prefix}-ip"
  ip_version   = "IPV4"
  address_type = "EXTERNAL"
  depends_on   = [google_project_service.required]
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_certificate_manager_dns_authorization" "web" {
  for_each   = local.domains
  name       = "${local.prefix}-${each.key}-auth"
  domain     = each.value
  type       = "PER_PROJECT_RECORD"
  depends_on = [google_project_service.required]
}

resource "google_certificate_manager_certificate" "web" {
  name = "${local.prefix}-cert"
  managed {
    domains            = sort(values(local.domains))
    dns_authorizations = [for auth in google_certificate_manager_dns_authorization.web : auth.id]
  }
}

resource "google_certificate_manager_certificate_map" "web" {
  name       = "${local.prefix}-certmap"
  depends_on = [google_project_service.required]
}

resource "google_certificate_manager_certificate_map_entry" "web" {
  for_each     = local.domains
  name         = "${local.prefix}-${each.key}"
  map          = google_certificate_manager_certificate_map.web.name
  certificates = [google_certificate_manager_certificate.web.id]
  hostname     = each.value
}

resource "google_compute_region_network_endpoint_group" "web" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${local.prefix}-web-neg"
  region                = "asia-southeast1"
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = "serp-web"
  }
  depends_on = [google_project_service.required]
}

resource "google_compute_backend_service" "web" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${local.prefix}-web-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  enable_cdn            = false
  # Serverless NEGs do not use health checks. No host/header rewrite or IAP.
  backend {
    group = google_compute_region_network_endpoint_group.web[0].id
  }
}

resource "google_compute_url_map" "http" {
  count = var.enable_load_balancer ? 1 : 0
  name  = "${local.prefix}-http"
  default_url_redirect {
    host_redirect          = "serpsaas.com"
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
    # No path_redirect/prefix_redirect: preserve the entire original path.
  }
}

resource "google_compute_url_map" "https" {
  count           = var.enable_load_balancer ? 1 : 0
  name            = "${local.prefix}-https"
  default_service = google_compute_backend_service.web[0].id
  host_rule {
    hosts        = ["www.serpsaas.com"]
    path_matcher = "www-canonical"
  }
  path_matcher {
    name = "www-canonical"
    default_url_redirect {
      host_redirect          = "serpsaas.com"
      https_redirect         = false
      redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
      strip_query            = false
    }
  }
}

resource "google_compute_target_http_proxy" "web" {
  count   = var.enable_load_balancer ? 1 : 0
  name    = "${local.prefix}-http-proxy"
  url_map = google_compute_url_map.http[0].id
}

resource "google_compute_target_https_proxy" "web" {
  count           = var.enable_load_balancer ? 1 : 0
  name            = "${local.prefix}-https-proxy"
  url_map         = google_compute_url_map.https[0].id
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.web.id}"
  depends_on      = [google_certificate_manager_certificate_map_entry.web]
}

resource "google_compute_global_forwarding_rule" "http" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${local.prefix}-http-rule"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  network_tier          = "PREMIUM"
  ip_address            = google_compute_global_address.web.id
  target                = google_compute_target_http_proxy.web[0].id
  port_range            = "80"
}

resource "google_compute_global_forwarding_rule" "https" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${local.prefix}-https-rule"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  network_tier          = "PREMIUM"
  ip_address            = google_compute_global_address.web.id
  target                = google_compute_target_https_proxy.web[0].id
  port_range            = "443"
}

output "load_balancer_ip" {
  value = google_compute_global_address.web.address
}

output "certificate_dns_records" {
  value = { for key, auth in google_certificate_manager_dns_authorization.web : key => auth.dns_resource_record[0] }
}
