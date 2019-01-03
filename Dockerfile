# Taken from https://hub.docker.com/r/garland/aws-cli-docker/~/dockerfile/

# install kaltura restore code 
# git@bitbucket.org:princeton/kaltura.git
FROM alpine:latest

RUN apk --no-cache update && \
    apk add bash && \
    # Install python2 and pip
    apk add --no-cache python2 && \
    python2 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip2 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip2 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python2 /usr/bin/python; fi && \
    rm -r /root/.cache && \
    # Install AWS SDK
    pip --no-cache-dir install boto3 awscli && \
    # Install Kaltura SDK
    pip --no-cache-dir install KalturaApiClient && \
	# get rid of apk cache
    rm -rf /var/cache/apk/*

# create /data and copy kaltura_Aws.py and its dependencies  
RUN mkdir /data
RUN mkdir /data/kaltura
ADD kaltura_aws.py /data/
ADD kaltura /data/kaltura/
ADD envvars.py /data/
# the video is not used when restorig videos - but kaltura_aws.py insists on its existance 
ADD placeholder_video.mp4 /data

# restore.rc is a bash script; it restores videos - saves log file, generates report of broken videos and copies them to s3
ADD restore.rc /data
RUN chmod 744 /data/restore.rc
RUN mkdir /data/log

# /data is now ready for work
WORKDIR /data
