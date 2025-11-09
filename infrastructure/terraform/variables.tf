# Terraform Variables for Room Boundary Detection System

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "room-detection"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_wall_detection_memory" {
  description = "Memory for wall detection Lambda (MB)"
  type        = number
  default     = 10240
}

variable "lambda_room_detection_memory" {
  description = "Memory for room detection Lambda (MB)"
  type        = number
  default     = 3008
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "s3_bucket_name" {
  description = "S3 bucket name for frontend hosting"
  type        = string
  default     = "room-detection-frontend"
}

variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}
