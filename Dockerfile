# Taken from https://hub.docker.com/r/garland/aws-cli-docker/~/dockerfile/

FROM alpine:3.8

# Versions: https://pypi.python.org/pypi/awscli#downloads
#ENV AWS_CLI_VERSION 1.11.131

RUN apk --no-cache update && \
    #apk --no-cache add python py-pip py-setuptools && \
    # Install python3 and pip
    apk add bash && \
    apk add --no-cache python2 && \
    python2 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip2 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip2 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python2 /usr/bin/python; fi && \
    rm -r /root/.cache && \
    # Install AWS SDK
    pip --no-cache-dir install boto3 && \
    # Install Kaltura SDK
    pip --no-cache-dir install KalturaApiClient && \
    rm -rf /var/cache/apk/*

WORKDIR /data

RUN mkdir /data/kaltura
ADD kaltura /data/kaltura/

ADD envvars.py /data/
ADD kaltura_aws.py /data/
ADD restore.rc /data

RUN mkdir /data/log


#RUN curl http://cdnbakmi.kaltura.com/content/clientlibs/python_02-10-2017.tar.gz | tar zx && \
#    (cd /data/python; python setup.py install)

RUN chmod 744 /data/restore.rc
