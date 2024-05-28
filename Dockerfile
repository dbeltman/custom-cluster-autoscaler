FROM python:3.12

ARG version=3.12
WORKDIR /app

# RUN apk add python-${version} py${version}-pip && \
# 	chown -R nonroot.nonroot /app/

# USER nonroot
COPY requirements.txt /app/
COPY example/config/reasons.yaml /config/reasons/reasons.yaml
RUN  pip install -r requirements.txt --user
COPY . .
ENTRYPOINT [ "python", "/app/main.py" ]