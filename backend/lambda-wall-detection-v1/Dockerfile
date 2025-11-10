# Use Python 3.11 slim image
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY ../shared ${LAMBDA_TASK_ROOT}/shared/

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Copy model weights
COPY models/ ${LAMBDA_TASK_ROOT}/models/

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Command
CMD ["app.main.handler"]

