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
 4. entry id 

Critera can be combined, except for selecting by tag and selecting by 'no lastPlayedAt'.

All actions that trigger changes, like archiving videos in s3 or replacing with the place holder video are 
perfomed in dryRun mode by default. 

Videos entries can be in three states: 
  1. initial
  2. archived 
  3. place_holder
  
In the initial state: 
  1. s3 does not contain a copy of the entry's original flavor 
  2. entry does not have the 'archived_to_s3' tag 
  3. entry does not have the 'deleted_flavors' tag 
  4. its original flavor is the entrys 'real' video - lets call this the real original flavor

In the archived state: 
  1. s3 contain a copy of the entry's real original flavor 
  2. entry has  the 'archived_to_s3' tag 
  3. entry does not have the 'deleted_flavors' tag 
  4. its original flavor is the real original flavor


In the  place_holder state: 
  1. s3 contain a copy of the entry's real original flavor 
  2. entry has  the 'archived_to_s3' tag 
  3. entry has the 'deleted_flavors' tag 
  4. its original flavor is the place holder video 
  

The kaltura_aws.py subcommands moves entries between states: 

~~~
    initial state -------- archive cmd  ------> archive state
    archive state -------- archive cmd  ------> archive state
    
    archive state -------- place_holder cmd --> place_holder state 
    place_holder state --- place_holder cmd --> place_holder state 
    
    place_holder state --- restore cmd -------> archived state 
~~~    

Subcommands print errors if they are applied to entries in a state that they can not work with, 
for example the place_holder command refuses to work with entries in the initial state. 

In addition kaltura_aws.py has a status subcommand. 


### kaltura_aws subcommands in pseudo code


#### archive 
~~~
if entry.original_flavor != None 
and if entry.original_flavor.status == READY 
and AWS bucket does not contain a file with the entries id 
   transfer to AWS-s3 bucket 
   apply 'archived_to_s3'  tag to entry
~~~


#### replace_video 

~~~
if entry.original_flavor != None 
and if entry.original_flavor.status == READY 
and AWS bucket contains a file with the entries id 
and that file has the same size as the original flavor
    delete all flavors including original  
    upload place holder video; create new thumbnail;
    apply tag 'flavors_deleted' 
~~~

#### status

check the following invariant - see kaltura_aws.entry_health_check method

~~~
has original flavor in READY status 
if AWS S3 contains a file with the entries ID 
    then the entry has the  'archived_to_s3' tag 
if the entry does not have the  'archived_to_s3' tag 
    then there is no entry in AWS 
if the entry dhas the  'flavors_deleted' tag 
    it should also have the 'archived_to_s3' tag
if the entry dows not have 'flavors_deleted' and has 'archived_to_s3' tag  
    size of original flavor and size of s3 entry should match  
if the entry does not have the 'flavors_deleted' tag 
    then the filesize of the AWS s3 entry matches the ORIGINAL flavors file size
~~~


## How to use 

to archive and replace with the place holder video choose a filter option 
that captures the videos you want to work on, then do: 
~~~

kaltura_aws.py  archive  [filter-options]
kaltura_aws.py  replace_video [filter-options]
kaltura_aws.py  status [filter-options]
~~~
   
The status command should list all selected videos in a HEALTHY state and all videos 
should be tagged 'archived_to_s3' and 'flavors_deleted' 

### Restoring Videos

Klatura updates the lastPlayedAt property of videos when they are played. 
So when a placeholder video is played it receives the current date as is its lastPlayedAt property

Apply the following steps to videos with the tag "archived_to_s3" that have been played within the last year

 1. Request restoral from AWS Glacier   IF not yet available in S3; This request will take 5 - 12 hours to complete.
 1. Restore Video:
   1. replace placeholder video with original video  IF video is availabe in S3
   1. recreate flavors and remove   tag: "flavors_deleted"    



### Edge case 

It is rare that videos are edited. Very few users have this ability. The procedure above will result in errors if

  1. a video is archived 
  1. a user replaces the original flavor with a new version  after archival 

The kaltura_aws.py command will error out when asked to replace the video unless the file size of the initial video and the versioned video are the same. 
So only if a video is replaced after archival which is unlikely since few users have that ability 
and if the versioned video has the same size, which is even more unlikely, will the procedure loose the versioned video. 


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
