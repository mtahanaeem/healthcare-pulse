FROM docker:28.1.1-cli AS docker-bin

FROM n8nio/n8n:latest

USER root

COPY --from=docker-bin /usr/local/bin/docker /usr/local/bin/docker

USER node
