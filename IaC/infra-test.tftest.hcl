# IaC/localstack.tftest.hcl

variables {
  is_local_test       = true
  eks_oidc_issuer_url = "https://localhost:4566"
}

run "verify_resources" {
  command = apply

  assert {
    condition     = aws_s3_bucket.user_avatars.force_destroy == true
    error_message = "S3 bucket must have force_destroy enabled in local tests."
  }

  assert {
    condition     = aws_dynamodb_table.users_table.name == "users-table"
    error_message = "DynamoDB table name mismatch."
  }

  assert {
    condition     = local.oidc_arn == "arn:aws:iam::000000000000:oidc-provider/localstack"
    error_message = "IAM Role is not using the mock LocalStack OIDC provider."
  }
}
