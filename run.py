#!/usr/bin/env python2
import subprocess

import os

# total = 13087

tsv = "list_creators-{}.tsv"
log = "list_creators-{}.log"
rng = range(1,27)
page_size = 500
cmd = 'python kaltura_aws.py list --first_page {} --page_size {} --max_entries {}'

def format_cmd_i(page_i, max):
    c = cmd.format(page_i, page_size, max)
    print(c)
    return c

def cmd_i(page_i, max):
    cmd = format_cmd_i(page_i, max)
    ftsv = open(tsv.format(page_i), "w")
    flog = open(log.format(page_i), "w")
    p = subprocess.Popen(cmd, stdout=ftsv, stderr=flog, close_fds=True, env=os.environ, cwd=os.getcwd(), shell=True)
    p.communicate()

if __name__ == '__main__':
    cmd_i( 1, 5000)
    cmd_i(11, 5000)
    cmd_i(21, 5000)


