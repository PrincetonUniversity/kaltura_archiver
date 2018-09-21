Kaltura
=======

The script [kaltura.py](kaltura.py) uses an action parameter. It can simply try to connect to the kaltura server,
list certain videos, backup/restore videos to AWS storage, 
or replace backed up videos with a placeholder video in the kaltura server

[kaltura.py](kaltura.py) relies on environment variables to authenticate against the Kaltura KMC  and AWS. 

Edit the template files  [bash.rc](bash.rc) and [csh.rc](csh.rc) set the relevant environment variables. 

Use [kaltura.py](kaltura.py)'s help option for further documentation 

~~~
python kaltura.py --help 
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
