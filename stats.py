from  kaltura_aws import KalturaArgParser, SAVED_TO_S3, PLACE_HOLDER_VIDEO
import kaltura
import envvars
import traceback
import sys

def setUp():
        params = envvars.to_value(KalturaArgParser.ENV_VARS)
        kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

def print_summary(pre, n, n_saved, n_pholder):
        print("{}: #{} {}".format(pre, 'TOTAL', n))
        print("{}: #{} {}".format(pre, SAVED_TO_S3, n_saved))
        print("{}: #{} {}".format(pre, PLACE_HOLDER_VIDEO, n_pholder))

def count():
        print "All: {}".format(kaltura.Filter().get_count())
        print "SAVED_TO_S3: {}".format(kaltura.Filter().tag(SAVED_TO_S3).get_count())
        print "PLACE_HOLDER_VIDEO: {}".format(kaltura.Filter().tag(PLACE_HOLDER_VIDEO).get_count())
        print("--")
        for year in range(10,0,-1):
                n = kaltura.Filter().years_since_played(year-1).played_within_years(year).get_count()
                if (n > 0):
                        print "lastPlayed between CUR-{} - CUR-{} years: {}".format(year, year-1, n)

        print("--")
        n, n_saved, n_pholder = 0, 0, 0
        try:
                for e in kaltura.Filter().undefined_LAST_PLAYED_AT():
                        n += 1
                        if (SAVED_TO_S3 in e.getTags()):
                                n_saved += 1
                        if (PLACE_HOLDER_VIDEO in e.getTags()):
                                n_pholder += 1
                        if (0 == n % 250):
                                sys.stdout.write('.'); sys.stdout.flush()
        except Exception as e:
                print(str(e))
                traceback.print_exc()
        print("\n")

        print "undefined_LAST_PLAYED_AT: {}".format(kaltura.Filter().undefined_LAST_PLAYED_AT().get_count())
        print_summary('undefined_LAST_PLAYED_AT', n, n_saved, n_pholder)


if __name__ == '__main__':
        setUp()
        count()