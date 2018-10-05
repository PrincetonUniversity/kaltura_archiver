Kaltura
=======

The script [kaltura_aws.py](kaltura_aws.py) is the main script to be run. 

It lists, archives and restores videos in Kaltura.  
It relies on environment variables to authenticate against the Kaltura KMC  and AWS. 
Start with  the template files  [bash.rc](bash.rc) and [csh.rc](csh.rc) set the relevant environment variables. 

Use the help option for further documentation 

~~~
python kaltura_aws.py --help 
~~~

## Archiving Videos Workflow 

Only videos that have not been played recently are archived. 

The [kaltura_aws.py](kaltura_aws.py)  provides parameters to select videos based on the following criteria: 

 1. number of years since placed
 2. whether video has no lastPlayedAt property 
 3. category id 
 3. tag value 

All actions, like downlading original flavors and storing in AWS, deleting derived flavors, deleting the original source video, 
or restoring sources and recreating derivates are performed in dryRun mode by default, that is the script logs actions but does not actually perform them. 

### Archiving Videos
Apply the following steps with the same video selection criterium, eg apply to all videos without a lastPlayedAt property:

Save to S3 pseudo code
~~~
if entry.original_flavor != None 
and if entry.original_flavor.status == READY 
and AWS bucket does not contain a file with the entries id 
   transfer to AWS-s3 bucket 
   apply 'archived_to_s3'  tag to entry
~~~


Replace with Place Holder video pseudo code
~~~
if entry.original_flavor != None 
and if entry.original_flavor.status == READY 
and AWS bucket contains a file with the entries id 
and that file has the same size as the original flavor
    delete all flavors including original  
    upload place holder video; create new thumbnail;
    apply tag 'flavors_deleted' 
~~~

TODO: Check that process was successfull, that is check each entry passes the follwowing tests:
~~~
has original flavor in READY status 
if AWS S3 contains a file with the entries ID 
    then the entry has the  'archived_to_s3' tag 
if the entry dows not have the  'archived_to_s3' tag 
    then there is not entry in AWS 
if the entry does not have the 'flavors_deleted' tag 
    then the filesize of the AWS s3 entry matches the ORIGINAL flavors file size
~~~

Run on command line:
~~~
kaltura_aws.py  archive  [filter-options]
kaltura_aws.py  replace_video [filter-options]
kaltura_aws.py  status [filter-options]
~~~
   

### Restoring Videos

Klatura updates the lastPlayedAt property of videos when they are played. 
So when a placeholder video is played it receives the current date as is its lastPlayedAt property

Apply the following steps to videos with the tag "archived_to_s3" that have been played within the last year

 1. Request restoral from AWS Glacier   IF not yet available in S3; This request will take 5 - 12 hours to complete.
 1. Restore Video:
   1. replace placeholder video with original video  IF video is availabe in S3
   1. recreate flavors and remove   tag: "flavors_deleted"
   


### See Early Requirements  
https://docs.google.com/document/d/1x-Snkv--fwuH8Yx3BBbbLr1sgIXA9Lhu5mAzTV5nfy0/edit


## Installation

### Python and Packages 

The code in the python subdirectory runs only with Python v2.x, see [.python-version](.python-version)

Please install pyenv according to  [github.com/pyenv/pyenv](https://github.com/pyenv/pyenv) 
Pyenv alows you ti install a local python copy and python libraries 
which functions independently of the system version. 

~~~
# install pyenv 
pyenv install 2.7 
pyenv versions
which python   # should show ~/.pyenv/shims/python
python -V      # should return Python 2.7
~~~

Install necessary packages 

~~~
curl -O http://cdnbakmi.kaltura.com/content/clientlibs/python_02-03-2017.tar.gz
pip install python_02-03-2017.tar.gz
pip install poster 

pip install  awscli --upgrade
~~~
