mock_provider "google" {}

run "certificate_stage_has_no_traffic_resources" {
  command = plan
  assert {
    condition     = length(google_compute_global_forwarding_rule.http) == 0 && length(google_compute_global_forwarding_rule.https) == 0 && length(google_compute_region_network_endpoint_group.web) == 0
    error_message = "Preparing certificate DNS must not enable any traffic path."
  }
  assert {
    condition     = google_certificate_manager_dns_authorization.web["apex"].type == "PER_PROJECT_RECORD" && google_certificate_manager_dns_authorization.web["www"].type == "PER_PROJECT_RECORD"
    error_message = "Avoid colliding with the existing Domain Mapping authorization."
  }
}

run "permanent_redirect_plan" {
  command = plan
  variables {
    enable_load_balancer = true
  }
  assert {
    condition     = google_compute_url_map.http[0].default_url_redirect[0].redirect_response_code == "MOVED_PERMANENTLY_DEFAULT" && google_compute_url_map.http[0].default_url_redirect[0].https_redirect && google_compute_url_map.http[0].default_url_redirect[0].host_redirect == "serpsaas.com" && !google_compute_url_map.http[0].default_url_redirect[0].strip_query
    error_message = "HTTP must redirect to HTTPS apex with 301 and preserve query."
  }
  assert {
    condition     = google_compute_url_map.http[0].default_url_redirect[0].path_redirect == null && google_compute_url_map.http[0].default_url_redirect[0].prefix_redirect == null
    error_message = "Do not replace the original path."
  }
  assert {
    condition     = one(google_compute_url_map.https[0].host_rule).hosts == toset(["www.serpsaas.com"]) && google_compute_url_map.https[0].path_matcher[0].default_url_redirect[0].redirect_response_code == "MOVED_PERMANENTLY_DEFAULT" && google_compute_url_map.https[0].path_matcher[0].default_url_redirect[0].host_redirect == "serpsaas.com" && !google_compute_url_map.https[0].path_matcher[0].default_url_redirect[0].https_redirect && !google_compute_url_map.https[0].path_matcher[0].default_url_redirect[0].strip_query
    error_message = "Only HTTPS www redirects; app/API host behavior stays outside this LB."
  }
  assert {
    condition     = google_compute_url_map.https[0].path_matcher[0].default_url_redirect[0].path_redirect == null && google_compute_url_map.https[0].path_matcher[0].default_url_redirect[0].prefix_redirect == null && !google_compute_backend_service.web[0].enable_cdn && google_compute_region_network_endpoint_group.web[0].cloud_run[0].service == "serp-web"
    error_message = "Preserve www path and route apex to the existing frontend without CDN caching."
  }
}
