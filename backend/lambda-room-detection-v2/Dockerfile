# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies and build tools
RUN yum install -y \
    mesa-libGL \
    gcc \
    gcc-c++ \
    make \
    && yum clean all

# Copy requirements
COPY lambda-room-detection-v2/requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared ${LAMBDA_TASK_ROOT}/shared/

# Copy Lambda function code
COPY lambda-room-detection-v2/app/ ${LAMBDA_TASK_ROOT}/app/

# Set proper permissions on Lambda handler files
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}/app/

# Set handler
CMD ["app.lambda_handler.handler"]

