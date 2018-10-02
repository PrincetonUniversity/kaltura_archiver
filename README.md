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

 1. Save to S3:
    1. if video does not exist in S3: download and store original 
    1. apply tag: "archived_to_s3" 
 1. Replace with Place Holder video 
    1. delete derived flavors  apply 'flavors_deleted' tag
        1. ONLY IFF video has original flavor 
        1. AND original flavor 'arrived' in AWS-S3 and has same size as original flavor 
        1. otherwise stop processing 
    1. delete original; 
    1. upload place holder video; create new thumbnail; 
    1. if successfull apply 'place_holder_video' tag 


~~~
kaltura_aws.py  archive  [filter-options]
kaltura_aws.py  replace_video [filter-options]
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
