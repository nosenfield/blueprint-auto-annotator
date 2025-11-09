# Lambda Function Code

This directory contains the AWS Lambda function code.

## Files

- **lambda_handler.py** - Lambda function entry point and handler
- **yolo_inference.py** - YOLO model loading and inference logic

## Usage

These files are copied into the Docker image during build (see `../Dockerfile`).

The Lambda handler is configured as `lambda_handler.handler` in the Dockerfile.

