# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for OpenCV and YOLO
RUN yum install -y \
    mesa-libGL \
    libgomp \
    && yum clean all

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Copy YOLO model weights
COPY models/ ${LAMBDA_TASK_ROOT}/models/

# Set the CMD to your handler
CMD ["app.main.handler"]
