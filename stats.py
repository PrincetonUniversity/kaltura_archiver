from kaltura_aws import KalturaArgParser, SAVED_TO_S3, PLACE_HOLDER_VIDEO
import kaltura
import envvars
import traceback
import sys
import logging

kaltura.logger.setLevel(logging.DEBUG)


def setUp():
    params = envvars.to_value(KalturaArgParser.ENV_VARS)
    kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])


def sum_sizes(filter):
    total = 0
    for e in filter:
        total += kaltura.MediaEntry(e).getTotalSize()
    return total

def KB_2_TB(total):
    return int(total ( 1024 * 1024))

def count():
    print "ALL: {}".format(kaltura.Filter().page_size(1).get_count())
    print "SAVED_TO_S3: {}".format(kaltura.Filter().page_size(1).tag(SAVED_TO_S3).get_count())
    print "PLACE_HOLDER_VIDEO: {}".format(kaltura.Filter().page_size(1).tag(PLACE_HOLDER_VIDEO).get_count())

    for year in range(10, 0, -1):
        f = kaltura.Filter().page_size(1000).years_since_played(year - 1).played_within_years(year)
        n = f.get_count()
        if (n > 0):
            print "PLAYED between CUR-{} - CUR-{} years: {}".format(year, year - 1, n)
            if (year == 1):
                totalTB =  KB_2_TB(sum_sizes(f))
                print "PLAYED between CUR-{} - CUR-{} years: {}   total-size TB {}".format(year, year - 1, totalTB)

    n, n_saved, n_pholder = 0, 0, 0
    try:
        for e in kaltura.Filter().undefined_LAST_PLAYED_AT():
            n += 1
            if (SAVED_TO_S3 in e.getTags()):
                n_saved += 1
            if (PLACE_HOLDER_VIDEO in e.getTags()):
                n_pholder += 1

    except Exception as e:
        print(str(e))
        traceback.print_exc()
    print("\n")

    pre = "undefined_LAST_PLAYED_AT"
    print "{}: {}".format(pre, kaltura.Filter().page_size(1).undefined_LAST_PLAYED_AT().get_count())
    print("{}: #{} {}".format(pre, 'TOTAL', n))
    print("{}: #{} {}".format(pre, SAVED_TO_S3, n_saved))
    print("{}: #{} {}".format(pre, PLACE_HOLDER_VIDEO, n_pholder))




if __name__ == '__main__':
    setUp()
    count()
