
Kaltura Archiving & Restoring in AWS 
====================================


Kaltura video archiving and restore actions are performed in docker containers that run as regularly scheduled Tasks in 
AWS ECS 'fargate-cluster'.  Images are stored in 'kaltura' AWS ECR repository.  Restorae and archive run as two different tasks 
that differ only in the command that is being executed, namely: [restore.rc](restore.rc) and [archive.rc](archive.rc)


## Docker  

Build Docker image and tag it with a name 
~~~
docker build --tag IMAGE_NAME .
~~~

Run script in a container 

~~~
docker run --env-file env.list  IMAGE_NAME  './restore.rc'
docker run --env-file env.list  IMAGE_NAME  './archive.rc'
~~~

where envlist is formatted as 

~~~
KALTURA_USERID=NETID@princeton.edu \
KALTURA_PARTNERID=P-ID \
KALTURA_SECRET=P-SECRET \
AWS_ACCESS_KEY_ID=A-ID \
AWS_SECRET_ACCESS_KEY=A-KEY \
AWS_BUCKET=BUCKET-NAME \
PLACEHOLDER_VIDEO=placeholder_video.mp4 \
~~~

### Locally Test Docker Image 

~~~
docker build -t test .

# list info on test image
docker images test 

# start container and enter sh 
docker run --env-file env.list -i -t test sh
~~~

## Update in AWS ECR repository


The related docker image is defined in the ECS `fargate-cluster`, 
which contains the `kaltura` image repository. 
The repository is where the latest Docker image based on the local [Dockerfile](./Dockerfile) is uploaded. 
The push commands are listed on the repository page in the AWS console and should be the same as used by the command:
~~~
docker_push
~~~

ECS also contains the task definitions to archive and restore videos.
Task definition, encapsulate the docker image to be run as well as 
environment variables to be passed to a container execution. 
Tasks schedules are defined in the 'fargate-cluster' 

## Trouble Shooting Incidents and Problems  

There is a kaltura dash board accessible in the AWS console called kaltura which can help with trouble shotting. 
Make sure you choose a time interval that goes back long enough for yor analysis. 

### Entry has not been restored - why ? 

First make sure in the Kaltura KMC whether the media entrys is still showing the replacement video. 
If so it should have the tags: 'archved_to_s3' and 'flavors_deleted'.

Look at the object with the name matching the video id  in s3://pu-kaltura-archive in the console. 
The object properties will tell you whether the file is in Glacier, S3, or in the process of being restored. 
If it is being restored give it more time to come out of Glacier. 

Otherwise have a loom at CloudWatch Logs to determine whether the restore process is even aware of the fact that 
the video should be restored.  Simply look whether the video id is mentioned anywhere in the /ecs/kaltura-restore cloudwatch log.

You can also sync the log reports stored in s3:pu-kaltura-archive: 
~~~
# download log reports from October 2019 
mkdir -p s3/2019/10
aws s3 sync s3://pu-kaltura-archive/log/2019/10/ s3/2019/10
~~~

This will deliver all logs not yet moved into GLacier to your local file system making it easier to look through them. 

### useful awscli commands

~~~
#list clusters
aws ecs list-clusters

# list currently active tasks 
aws ecs list-tasks --cluster fargate-cluster 

# list arns of kaltura tasks definitions 
aws ecs list-task-definitions | fgrep  kaltura

# task definition details  
aws ecs describe-task-definition --task-definition "arn:aws:ecs:us-east-1:168298894881:task-definition/kaltura-archive"

~~~
 

