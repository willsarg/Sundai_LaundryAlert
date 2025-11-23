# IAM role for Lambda execution
resource "aws_iam_role" "lambda_exec" {
  name = "laundry_alert_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic Lambda execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_exec.name
}

# S3 access policy for Lambda
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "lambda_s3_access"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.laundry_alert.arn,
          "${aws_s3_bucket.laundry_alert.arn}/*"
        ]
      }
    ]
  })
}

# Lambda layer for numpy and scipy
resource "aws_lambda_layer_version" "scipy_numpy" {
  filename            = "${path.module}/lambdas/scipy_numpy_layer.zip"
  layer_name          = "scipy-numpy-layer"
  compatible_runtimes = ["python3.11"]
  source_code_hash    = filebase64sha256("${path.module}/lambdas/scipy_numpy_layer.zip")
}

# Build Lambda package with dependencies
resource "null_resource" "build_lambda" {
  triggers = {
    requirements = filemd5("${path.module}/lambdas/processor/requirements.txt")
    lambda_code  = sha256(join("", [for f in fileset("${path.module}/lambdas/processor", "*.py") : filesha256("${path.module}/lambdas/processor/${f}")]))
  }

  provisioner "local-exec" {
    command = "${path.module}/build_lambda.sh"
  }
}

# Lambda function
resource "aws_lambda_function" "processor" {
  filename         = "${path.module}/lambdas/processor_with_deps.zip"
  function_name    = "laundry-alert-processor"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/lambdas/processor_with_deps.zip")
  runtime          = "python3.11"
  timeout          = 30

  # Use custom Lambda layer for numpy and scipy
  layers = [
    aws_lambda_layer_version.scipy_numpy.arn
  ]

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.laundry_alert.id
    }
  }

  depends_on = [null_resource.build_lambda]
}

# Allow S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.laundry_alert.arn
}

# S3 bucket notification to trigger Lambda on .wav uploads
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.laundry_alert.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".wav"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# Outputs
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.processor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.processor.arn
}
