resource "aws_s3_bucket" "user_avatars" {
  bucket = "user-avatars"
  force_destroy = var.is_local_test
}

resource "aws_dynamodb_table" "users_table" {
  name         = "users-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "email"

  tags = {
    Environment = var.is_local_test ? "localstack" : "production"
  }

  attribute {
    name = "email"
    type = "S"
  }

  lifecycle {
    ignore_changes = [
      read_capacity,
      write_capacity
    ]
  }
}

resource "aws_iam_policy" "app_policy" {
  name        = "user-management-policy"
  description = "Allows FastAPI to access S3 and DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.users_table.arn
      },
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.user_avatars.arn}/*"
      }
    ]
  })
}

data "aws_iam_openid_connect_provider" "oidc_provider" {
  count = var.is_local_test ? 0 : 1
  url   = var.eks_oidc_issuer_url
}

locals {
  oidc_url_stripped = replace(var.eks_oidc_issuer_url, "https://", "")

  # For LocalStack, use a dummy ARN. For AWS, use the data source.
  oidc_arn = var.is_local_test ? "arn:aws:iam::000000000000:oidc-provider/localstack" : data.aws_iam_openid_connect_provider.oidc_provider[0].arn
}

resource "aws_iam_role" "app_role" {
  name = "user-management-eks-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url_stripped}:sub" = "system:serviceaccount:default:user-management-sa"
            "${local.oidc_url_stripped}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app_attach" {
  role       = aws_iam_role.app_role.name
  policy_arn = aws_iam_policy.app_policy.arn
}
