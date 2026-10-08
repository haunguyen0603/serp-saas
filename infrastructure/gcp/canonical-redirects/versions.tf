terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = "serp-saas"
  region  = "asia-southeast1"
}
