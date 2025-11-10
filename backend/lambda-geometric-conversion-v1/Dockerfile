FROM public.ecr.aws/lambda/python:3.11

COPY lambda-geometric-conversion-v1/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ${LAMBDA_TASK_ROOT}/shared/
COPY lambda-geometric-conversion-v1/app/ ${LAMBDA_TASK_ROOT}/app/

WORKDIR ${LAMBDA_TASK_ROOT}

CMD ["app.main.handler"]

