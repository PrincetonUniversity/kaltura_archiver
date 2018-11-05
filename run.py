#!/usr/bin/env python2
import subprocess

import os

# total = 13087

tsv = "list_creators-{}.tsv"
log = "list_creators-{}.log"
rng = range(1,15)
page_size = 1000
cmd = 'python kaltura_aws.py list  -n  --first_page {} --page_size {} --max_entries {}'

def cmd_i(i):
    return cmd.format(i, page_size, page_size)

if __name__ == '__main__':
    for i in  rng:
        ftsv = open(tsv.format(i), "w")
        flog = open(log.format(i), "w")
        p = subprocess.Popen(cmd_i(i), stdout=ftsv, stderr=flog, close_fds=True, env=os.environ, cwd=os.getcwd(), shell=True)
