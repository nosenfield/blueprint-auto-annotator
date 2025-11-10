# Use Python 3.11 slim image
FROM public.ecr.aws/lambda/python:3.11

# Install minimal system dependencies for headless OpenCV
# We DON'T need GUI libraries (mesa-libGL, etc.) because we're using opencv-python-headless
RUN yum install -y \
    gcc \
    gcc-c++ \
    make \
    && yum clean all

# Environment variables to disable GUI/display features
ENV MPLBACKEND=Agg
ENV OPENCV_VIDEOIO_PRIORITY_MSMF=0
ENV QT_QPA_PLATFORM=offscreen

# Copy requirements
COPY lambda-wall-detection-v1/requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies - opencv-python conflict workaround
# ultralytics pulls in opencv-python (GUI version) which we don't want
# Solution: Install, then swap for headless without triggering numpy rebuild
RUN pip install --no-cache-dir 'numpy==1.24.3' && \
    pip install --no-cache-dir 'torch==2.1.0' 'torchvision==0.16.0' && \
    pip install --no-cache-dir -r requirements.txt && \
    # Uninstall GUI opencv and install headless (don't use --force-reinstall to avoid numpy rebuild)
    pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless && \
    pip install --no-cache-dir --no-deps 'opencv-python-headless==4.8.1.78' && \
    # Verify installation
    pip list | grep opencv && \
    python -c "import sys; import numpy; import cv2; print(f'NumPy: {numpy.__version__}, OpenCV: {cv2.__version__}')"

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

