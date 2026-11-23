
# Package Transform Lambda
data "archive_file" "transform_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/transform"
  output_path = "${path.module}/build/transform.zip"
}

# CloudWatch logs
resource "aws_cloudwatch_log_group" "transform" {
  name              = "/aws/lambda/yt-transform"
  retention_in_days = 7
}

# IAM role
resource "aws_iam_role" "transform" {
  name = "yt-transform-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# CloudWatch logging permission
resource "aws_iam_role_policy_attachment" "transform_logs" {
  role       = aws_iam_role.transform.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 and SQS permissions
resource "aws_iam_role_policy" "transform_access" {
  name = "yt-transform-access"
  role = aws_iam_role.transform.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::${var.bucket_name}/raw/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.bucket_name}/curated/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.raw_events.arn
      }
    ]
  })
}

# Transform Lambda
resource "aws_lambda_function" "transform" {
  function_name = "yt-transform"
  role          = aws_iam_role.transform.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"

  filename         = data.archive_file.transform_zip.output_path
  source_code_hash = data.archive_file.transform_zip.output_base64sha256

  timeout     = 60
  memory_size = 512

  layers = [var.pandas_layer_arn]

  depends_on = [
    aws_cloudwatch_log_group.transform
  ]
}

# Connect SQS to Transform Lambda
resource "aws_lambda_event_source_mapping" "transform_sqs" {
  event_source_arn = aws_sqs_queue.raw_events.arn
  function_name    = aws_lambda_function.transform.arn
  batch_size       = 1
  enabled          = true
}
