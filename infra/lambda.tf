data "archive_file" "ingest_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/ingest"
  output_path = "${path.module}/build/ingest.zip"
  excludes    = ["manual_ingest.py", "__pycache__"]
}

resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/yt-ingest"
  retention_in_days = 7
}

resource "aws_lambda_function" "ingest" {
  function_name    = "yt-ingest"
  role             = aws_iam_role.ingest.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.ingest_zip.output_path
  source_code_hash = data.archive_file.ingest_zip.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      BUCKET    = var.bucket_name
      QUEUE_URL = aws_sqs_queue.raw_events.url
    }
  }

  depends_on = [aws_cloudwatch_log_group.ingest]
}