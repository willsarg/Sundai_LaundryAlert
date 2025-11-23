resource "aws_dynamodb_table" "laundry_events" {
  name         = "LaundryEvents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "filename"
  range_key    = "timestamp"

  attribute {
    name = "filename"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  tags = {
    Environment = "hackathon"
    Project     = "Sundai Laundry Alert"
  }
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.laundry_events.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.laundry_events.arn
}
