#!/usr/bin/env bash
# Create (idempotently) and harden the two S3 buckets EPIConnect needs, with
# the AWS CLI rather than Terraform:
#   epiconnect-tfstate-<account>  Terraform remote state (must exist before `terraform init`)
#   epiconnect-media-<account>    user uploads (the Terraform AWS provider reads each
#                                 bucket's Object Lock configuration, which the AWS
#                                 Academy service control policy denies)
# Both: private, public access blocked, SSE-S3, TLS-only bucket policy.
# stdout carries only the state bucket name (captured by the workflow).
set -euo pipefail
exec 3>&1 1>&2
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
STATE_BUCKET="epiconnect-tfstate-${ACCOUNT}"
MEDIA_BUCKET="epiconnect-media-${ACCOUNT}"

harden() { # bucket
  local bucket="$1"
  if ! aws s3api head-bucket --bucket "$bucket" >/dev/null 2>&1; then
    aws s3api create-bucket --bucket "$bucket" --region "$REGION" >/dev/null
    echo "created $bucket"
  fi
  aws s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-ownership-controls --bucket "$bucket" \
    --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'
  aws s3api put-bucket-encryption --bucket "$bucket" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}'
  aws s3api put-bucket-policy --bucket "$bucket" --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{\"Sid\": \"DenyInsecureTransport\", \"Effect\": \"Deny\", \"Principal\": \"*\", \"Action\": \"s3:*\",
      \"Resource\": [\"arn:aws:s3:::${bucket}\", \"arn:aws:s3:::${bucket}/*\"],
      \"Condition\": {\"Bool\": {\"aws:SecureTransport\": \"false\"}}}]}"
  echo "$bucket: private, encrypted, TLS-only"
}

harden "$STATE_BUCKET"
# State history: every write is kept, a bad apply can be rolled back
aws s3api put-bucket-versioning --bucket "$STATE_BUCKET" --versioning-configuration Status=Enabled
harden "$MEDIA_BUCKET"

echo "$STATE_BUCKET" >&3
