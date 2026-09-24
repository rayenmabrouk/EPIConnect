terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  # Remote state: bucket name is account-specific and passed at init time
  #   terraform init -backend-config="bucket=epiconnect-tfstate-<account-id>"
  # use_lockfile = S3-native locking (no DynamoDB table).
  backend "s3" {
    key          = "epiconnect/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Repo      = "rayenmabrouk/EPIConnect"
    }
  }
}

# Same account/region without default tags: used for CloudFront, because
# creating a tagged distribution also needs cloudfront:TagResource, which the
# AWS Academy role may not have.
provider "aws" {
  alias  = "untagged"
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
