FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared ${LAMBDA_TASK_ROOT}/shared/
COPY app/ ${LAMBDA_TASK_ROOT}/app/

WORKDIR ${LAMBDA_TASK_ROOT}

CMD ["app.main.handler"]

