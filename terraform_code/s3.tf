resource "aws_s3_bucket" "laundry_alert" {
  bucket = "sundai-laundry-alert-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "laundry_alert" {
  bucket = aws_s3_bucket.laundry_alert.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "laundry_alert" {
  bucket = aws_s3_bucket.laundry_alert.id

  versioning_configuration {
    status = "Disabled"
  }
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.laundry_alert.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.laundry_alert.arn
}
