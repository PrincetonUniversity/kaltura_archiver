#!/usr/bin/env python
from kaltura_aws import KalturaArgParser, SAVED_TO_S3, PLACE_HOLDER_VIDEO, DEFAULT_STATUS_LIST
import kaltura
import envvars
import traceback
import sys
import logging

kaltura.logger.setLevel(logging.DEBUG)


def setUp():
    params = envvars.to_value(KalturaArgParser.ENV_VARS)
    formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
    if (False):
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
            print "PLAYED between CUR-{} - CUR-{} years: {}   total-size TB {}".format(year, year - 1, n ,totalTB)
        else:
            print "PLAYED between CUR-{} - CUR-{} years: {}".format(year, year - 1, n)
    return n

def count():
    print "ALL: {}".format(kaltura.Filter().page_size(1).status(DEFAULT_STATUS_LIST).get_count())
    print "SAVED_TO_S3: {}".format(kaltura.Filter().page_size(1).status(DEFAULT_STATUS_LIST).tag(SAVED_TO_S3).get_count())
    print "PLACE_HOLDER_VIDEO: {}".format(kaltura.Filter().page_size(1).status(DEFAULT_STATUS_LIST).tag(PLACE_HOLDER_VIDEO).get_count())

    sum = 0
    for year in range(5, 0, -1):
        sum += year_status(year, False)

    pre = "undefined_LAST_PLAYED_AT"
    n_noLastPLayed = kaltura.Filter().page_size(1).status(DEFAULT_STATUS_LIST).undefined_LAST_PLAYED_AT().get_count()
    print "{}: {}".format(pre, n_noLastPLayed)
    sum = sum + n_noLastPLayed
    print("{}: #{} {}".format(pre, 'TOTAL', sum))

    print('')
    print("{}: #{} {}".format(pre, 'TOTAL', n_noLastPLayed))
    n, n_saved, n_pholder = 0, 0, 0
    try:
        for e in kaltura.Filter().page_size(1000).status(DEFAULT_STATUS_LIST).undefined_LAST_PLAYED_AT():
            n += 1
            if (SAVED_TO_S3 in e.getTags()):
                n_saved += 1
            if (PLACE_HOLDER_VIDEO in e.getTags()):
                n_pholder += 1
    except Exception as e:
        print(str(e))
        traceback.print_exc()
    print("{}: #{} {}".format(pre, 'TOTAL', n))
    print("{}: #{} {}".format(pre, SAVED_TO_S3, n_saved))
    print("{}: #{} {}".format(pre, PLACE_HOLDER_VIDEO, n_pholder))

    if (False):
        print("")
        print("TB of videos played in last year - ... - will take a while to compute")
        year_status(1, True)

if __name__ == '__main__':
    setUp()
    count()
