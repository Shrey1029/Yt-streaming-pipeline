
resource "aws_sqs_queue" "dlq" {
  name                      = "yt-raw-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "raw_events" {
  name                       = "yt-raw-events"
  visibility_timeout_seconds = 360

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
