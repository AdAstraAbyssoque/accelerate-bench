ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG ROLE
USER root
COPY cohort-source.tar.gz /tmp/cohort-source.tar.gz
COPY cohort-source-files.json /tmp/cohort-source-files.json
COPY cohort-rebuild.py /tmp/cohort-rebuild.py
RUN python3 -B /tmp/cohort-rebuild.py "${ROLE}"
LABEL accelerate.mhm2.cohort="mhm2-reference-sam-adapter-v1"
