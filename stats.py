from  kaltura_aws import KalturaArgParser, SAVED_TO_S3, PLACE_HOLDER_VIDEO
import kaltura
import envvars
import traceback

def setUp():
        params = envvars.to_value(KalturaArgParser.ENV_VARS)
        kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

def print_summary(n, n_saved, n_pholder):
        print("#{} {}".format('TOTAL', n))
        print("#{} {}".format(SAVED_TO_S3, n_saved))
        print("#{} {}".format(PLACE_HOLDER_VIDEO, n_pholder))

def count():
        filter = kaltura.Filter()
        n, n_saved, n_pholder = 0, 0, 0
        try:
                for e in filter:
                        n += 1
                        if (SAVED_TO_S3 in e.getTags()):
                                n_saved += 1
                        if (PLACE_HOLDER_VIDEO in e.getTags()):
                                n_pholder += 1
                        if (0 == n % 500):
                                print_summary(n, n_saved, n_pholder)
        except Exception as e:
                print(str(e))
                traceback.print_exc()
        print("---")
        print_summary(n, n_saved, n_pholder)


if __name__ == '__main__':
        setUp()
        count()