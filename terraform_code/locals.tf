locals {
  default_tags = {
    Project     = "Sundai_LaundryAlert"
    Owner       = "will"
    Environment = "dev"
    CreatedBy   = "terraform"
    CreatedAt   = "2025-11-23"
  }

  tags = merge(local.default_tags, var.tags)
}
