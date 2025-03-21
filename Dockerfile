FROM python:3.12-alpine

WORKDIR /app

RUN apk add python-3.12 py3.12-pip && \
	chown -R nonroot.nonroot /app/

USER nonroot
COPY requirements.txt /app/
COPY example/config/reasons.yaml /config/reasons/reasons.yaml
RUN  pip install -r requirements.txt --user
COPY . .
ENTRYPOINT [ "python", "/app/main.py" ]
