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

## Workflow 

see https://docs.google.com/document/d/1x-Snkv--fwuH8Yx3BBbbLr1sgIXA9Lhu5mAzTV5nfy0/edit

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
