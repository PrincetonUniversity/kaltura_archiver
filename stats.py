#!/usr/bin/env python
from kaltura_aws import KalturaArgParser, SAVED_TO_S3, PLACE_HOLDER_VIDEO, DEFAULT_STATUS_LIST
import kaltura
import envvars
import traceback
import sys
import logging

kaltura.logger.setLevel(logging.DEBUG)

DEFAULT_FILTER_STATUS_LIST = ",".join(DEFAULT_STATUS_LIST)


def setUp():
    params = envvars.to_value(KalturaArgParser.ENV_VARS)
    # turn to True for lots of logging
    if (False):
        formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        kaltura.logger.addHandler(handler)
        logging.root.setLevel(logging.DEBUG)
        kaltura.logger.setLevel('DEBUG')
    kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])


def sum_sizes(filter):
    total = 0
    for e in filter:
        total += kaltura.MediaEntry(e).getTotalSize()
    return total

def KB_2_TB(total):
    return int(total / ( 1024 * 1024))

def year_status(year, sizes=False):
    f = kaltura.Filter().page_size(1000).years_since_played(year - 1).played_within_years(year)
    n = f.get_count()
    if (n > 0):
        if (sizes):
            totalTB =  KB_2_TB(sum_sizes(f))
            print "PLAYED between CUR-{} - CUR-{} years: #videos: {}  total-size TB {}".format(year, year - 1, n ,totalTB)
        else:
            print "PLAYED between CUR-{} - CUR-{} years: #videos: {}".format(year, year - 1, n)
    return n

def play_info_creation_year(year):
    f = kaltura.Filter().page_size(1000).years_since_created(year-1).created_wthin_years(year)
    n = f.get_count()
    f = f.tag(PLACE_HOLDER_VIDEO)
    n_placeholder = f.get_count()
    if (n > 0):
        print "CREATED between CUR-{} - CUR-{} years: #videos: {}   #place-holder {}".format(year, year - 1, n, n_placeholder)

def count():
    flter = kaltura.Filter().page_size(1).status(DEFAULT_FILTER_STATUS_LIST)
    print(str(flter))
    print "ALL: {}".format(kaltura.Filter().page_size(1).status(DEFAULT_FILTER_STATUS_LIST).get_count())
    print "SAVED_TO_S3: {}".format(kaltura.Filter().page_size(1).status(DEFAULT_FILTER_STATUS_LIST).tag(SAVED_TO_S3).get_count())
    print "PLACE_HOLDER_VIDEO: {}".format(kaltura.Filter().page_size(1).status(DEFAULT_FILTER_STATUS_LIST).tag(PLACE_HOLDER_VIDEO).get_count())
    print("")

    for year in range(8, 0, -1):
        play_info_creation_year(year)
    print("")

    sum = 0
    for year in range(5, 0, -1):
        sum += year_status(year, False)
    print("")

    if (True):
        print("")
        print("TB of videos played in last year - ... - will take a while to compute")
        year_status(1, True)

if __name__ == '__main__':
    setUp()
    count()
