resource "aws_scheduler_schedule" "ingest" {
  name                = "yt-ingest-every-15-min"
  schedule_expression = "rate(15 minutes)"
  state               = "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.ingest.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}