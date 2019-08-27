# Taken from https://hub.docker.com/r/garland/aws-cli-docker/~/dockerfile/

# install kaltura restore code 
# git@bitbucket.org:princeton/kaltura.git
FROM alpine:latest as build

RUN apk --no-cache update && \
    apk add --no-cache  bash && \
    # Install python2 and pip
    apk add --no-cache python2 && \
    python2 -m ensurepip && \
    pip2 install --upgrade pip setuptools && \
    # Install AWS SDK
    pip2 install --no-cache-dir  boto3 awscli && \
    # Install Kaltura SDK
    pip2 install --no-cache-dir KalturaApiClient==3.3.1
RUN pip2  uninstall -y pip setuptools

FROM alpine:latest
RUN apk add --no-cache bash
RUN apk add  --no-cache  python2
RUN mkdir /site-packages
COPY --from=build  /usr/lib/python2.7/site-packages /site-packages
ENV PYTHONPATH /site-packages

WORKDIR /data
RUN mkdir -p /data/src /data/log
ADD src /data/src/
ADD *.rc  placeholder*  /data/

# put latest commit hash in dedicated file 
# does not work when in detached mode - but should not build image anyway 
RUN mkdir /git
WORKDIR /git
ADD .git/HEAD /git
ADD .git/refs/heads /git
RUN sed 's,.*/,,' HEAD > /data/BRANCH
RUN cat `cat /data/BRANCH`  > /data/COMMIT-HASH

WORKDIR /data





