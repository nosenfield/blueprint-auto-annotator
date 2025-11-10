# Use Python 3.11 slim image
FROM public.ecr.aws/lambda/python:3.11

# Install build dependencies for matplotlib
RUN yum install -y gcc gcc-c++ make && \
    yum clean all

# Copy requirements
COPY lambda-wall-detection-v1/requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared ${LAMBDA_TASK_ROOT}/shared/

# Copy application code
COPY lambda-wall-detection-v1/app/ ${LAMBDA_TASK_ROOT}/app/

# Copy model weights
COPY lambda-wall-detection-v1/models/ ${LAMBDA_TASK_ROOT}/models/

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Command
CMD ["app.main.handler"]

