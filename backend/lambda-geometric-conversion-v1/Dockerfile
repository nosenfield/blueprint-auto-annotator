FROM public.ecr.aws/lambda/python:3.11

# Minimal system dependencies (no GUI libraries needed for opencv-python-headless)
RUN yum install -y \
    gcc \
    gcc-c++ \
    make \
    && yum clean all

# Environment variables to disable GUI/display features
ENV MPLBACKEND=Agg
ENV OPENCV_VIDEOIO_PRIORITY_MSMF=0
ENV QT_QPA_PLATFORM=offscreen

COPY lambda-geometric-conversion-v1/requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies, then swap for opencv-headless
RUN pip install --no-cache-dir 'numpy==1.24.3' && \
    pip install --no-cache-dir -r requirements.txt && \
    # Swap opencv versions without rebuilding numpy
    pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless && \
    pip install --no-cache-dir --no-deps 'opencv-python-headless==4.8.1.78' && \
    # Verify installation
    pip list | grep opencv && \
    python -c "import numpy; import cv2; print(f'NumPy: {numpy.__version__}, OpenCV: {cv2.__version__}')"

COPY shared ${LAMBDA_TASK_ROOT}/shared/
COPY lambda-geometric-conversion-v1/app/ ${LAMBDA_TASK_ROOT}/app/

WORKDIR ${LAMBDA_TASK_ROOT}

CMD ["app.main.handler"]

