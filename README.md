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
Only videos smaller than  10000000kb are archived
 

The [kaltura_aws.py](kaltura_aws.py)  provides parameters to select videos based on the following criteria: 

 1. number of years since placed
 2. whethertion date   
 3. category id 
 3. tag value 
 3. the number of times the video was played 
 4. status of entry - eg READY (2), QUEDE (0), ERROR (-1), .. see   KalturaEntryStatus class in KalturaClient.Plugins.Core 
 5. entry id 

Most critera can be combined.

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
  4. its original flavor is the entry's 'real' video - lets call this the real original flavor

In the archived state: 
  1. s3 contain a copy of the entry's real original flavor 
  2. entry has  the 'archived_to_s3' tag 
  3. entry does not have the 'deleted_flavors' tag  -- same as initial state
  4. its original flavor is the real original flavor  -- same as initial state


In the  place_holder state: 
  1. s3 contain a copy of the entry's real original flavor -- same as archived state
  2. entry has  the 'archived_to_s3' tag -- same as archived state
  3. entry has the 'deleted_flavors' tag 
  4. its original flavor is the place holder video 
  

The kaltura_aws.py subcommands moves entries between states: 

~~~
    initial state -------- copy cmd  ------> archive state
    archive state -------- copy cmd  ------> archive state
    
    archive state -------- place_holder cmd --> place_holder state 
    place_holder state --- place_holder cmd --> place_holder state 
    
    place_holder state --- restore cmd -------> archived state 
~~~    

Subcommands print errors if they are applied to entries in a state that they can not work with, 
for example the place_holder command refuses to work with entries in the initial state. 

In addition kaltura_aws.py has a health and count subcommands. 


### kaltura_aws subcommands in pseudo code


#### archive 
~~~
if entry.original_flavor != None 
and if entry.original_flavor.status == READY 
and AWS bucket does not contain a file with the same name as entries id 
   transfer to AWS-s3 bucket 
   apply 'archived_to_s3'  tag to entry
~~~


#### replace_video 

~~~
if entry.original_flavor != None 
and if entry.original_flavor.status == READY 
and AWS bucket contains a file with the same name as entries id 
and that file has the same size as the original flavor
    delete all flavors including original  
    upload place holder video; create new thumbnail;
    apply tag 'flavors_deleted' 
    wait until entry goes into READY state (sleep in between checks) 
~~~

#### health

check the following invariant - see kaltura_aws.entry_health_check method

~~~
has original flavor and is in READY status 
if AWS S3 contains a file with the entries ID 
    then the entry has the  'archived_to_s3' tag 
if the entry does not have the  'archived_to_s3' tag 
    then there is no entry in AWS 
if the entry has the  'flavors_deleted' tag 
    it should also have the 'archived_to_s3' tag
if the entry does not have 'flavors_deleted' and has 'archived_to_s3' tag  
    size of original flavor and size of s3 entry should match  
~~~


## How to use 

to archive and replace with the place holder video choose a filter option 
that captures the videos you want to work on, then do: 
~~~
kaltura_aws.py  s3copy   [fiOlter-options]
kaltura_aws.py  replace_video [filter-options]
kaltura_aws.py  health [filter-options]
~~~
   
The health command should list all selected videos in a HEALTHY state and all videos 
should be tagged 'archived_to_s3' and 'flavors_deleted' 

To count matchig videos
~~~
#entries with archived_to_s3
kaltura_aws.py count --tag archived_to_s3  
#entries without archived_to_s3
kaltura_aws.py count --tag !archived_to_s3  

# entries that were played between 2-3 years ago 
kaltura_aws.py count --played_within 3 --unplayed_for 2

# entries that are not in the READY state
./kaltura_aws.py count --status --status 1 -2 0 1 7 4
~~~


To list videos that were created 3-4 years ago but never plyed: 
~~~
python kaltura_aws.py list --created_before 3 --created_within 4 --plays 0
~~~

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

### reports ### 

### video list with creator ids and their ldap status ### 
Use this report to generate a list of videos with information on the creator associated with the entry: 
   1. creators netid 
   1. active/inactive according to ldap 
   1. name 
   1. org unit 
   
   
ldap expression that determines whether an account is active: 
~~~
(&(uid=<NETID>)(|(puresource=authentication=enabled)(puresource=authentication=goingaway)))
~~~

~~~ 
./kaltura_aws.py list   [filter-options]a > list.tsv 
cat list.tsv | add_ldap_status.py > emhanced_list.tsv 
~~~

### rough statistics ###

counts video entries that have been played in the laste 20 years 

cmputes TB of entries that were played in the last year 

~~~
stats.py
~~~

### See Early Requirements  
https://docs.google.com/document/d/1x-Snkv--fwuH8Yx3BBbbLr1sgIXA9Lhu5mAzTV5nfy0/edit


## Troubleshooting 

### Manually test ldap credentials/search on CLI

run on the command line  - you may have to install the [openldap package](http://www.openldap.org)

on EC2 server run 'sudo yum install openldap-clients'

Look for 'puresource=authentication=disabled' ; print only dn property
~~~
ldapsearch -LLL -x -H "ldaps://$LDAP_SERVER/" -b "o=Princeton University,c=US" -D "uid=NETID,o=princeton university,c=us" -W 'puresource=authentication=disabled' 1.1
~~~

Look for entries with a valid uid and with no pususpended value; in addition to dn, print uid and puresource properties
~~~
ldapsearch -LLL -x -H "ldaps://$LDAP_SERVER/" -b "o=Princeton University,c=US" -D "uid=NETID,o=princeton university,c=us" -W '(&(uid=*)(!(pususpended=*)))' uid puresource
~~~


## Execute Tests 

set environment variabes so code connects to TEST KMC, then run: 

~~~
python -m unittest discover -v test
~~~

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
