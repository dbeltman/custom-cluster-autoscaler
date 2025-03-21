FROM python:3.12-alpine

WORKDIR /app

RUN	chown -R nonroot: /app/

USER nonroot
COPY requirements.txt /app/
COPY example/config/reasons.yaml /config/reasons/reasons.yaml
RUN  pip install -r requirements.txt --user
COPY . .
ENTRYPOINT [ "python", "/app/main.py" ]
