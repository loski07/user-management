provider "aws" {
  region = "us-east-1"

  dynamic "endpoints" {
    for_each = var.is_local_test ? [1] : []
    content {
      s3       = "http://localhost:4566"
      dynamodb = "http://localhost:4566"
      iam      = "http://localhost:4566"
      sts      = "http://localhost:4566"
    }
  }

  s3_use_path_style           = var.is_local_test
  skip_credentials_validation = var.is_local_test
  skip_metadata_api_check     = var.is_local_test
  skip_requesting_account_id  = var.is_local_test

  access_key = var.is_local_test ? "test" : null
  secret_key = var.is_local_test ? "test" : null
}
