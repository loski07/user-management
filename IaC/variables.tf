variable "is_local_test" {
  type        = bool
  default     = false
  description = "Defines if the terraform will target Localstack instead for the final AWS account"
}

variable "eks_oidc_issuer_url" {
  type        = string
  default     = "https://localhost:4566"
  description = "The URL of the OIDC Identity Provider (e.g. https://oidc.eks.us-east-1.amazonaws.com/id/XXX)"
}
