
variable "region" {
  default = "ap-south-1"
}

variable "bucket_name" {
  default = "yt-pipeline-shreyansh-raw"
}

variable "schedule_enabled" {
  default = true
}

variable "pandas_layer_arn" {
  description = "AWS SDK for pandas Lambda layer ARN"
  type        = string
  default     = "arn:aws:lambda:ap-south-1:336392948345:layer:AWSSDKPandas-Python312:1"
}
