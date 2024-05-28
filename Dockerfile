FROM cgr.dev/chainguard/wolfi-base

ARG version=3.12
WORKDIR /app

RUN apk add python-${version} py${version}-pip && \
	chown -R nonroot.nonroot /app/

USER nonroot
COPY requirements.txt /app/
RUN  pip install -r requirements.txt --user
COPY . .
RUN find /app
ENTRYPOINT [ "python", "/app/main.py" ]