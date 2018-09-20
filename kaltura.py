from KalturaClient import *
from KalturaClient.Plugins.Core import *

import logging, traceback
from argparse import RawDescriptionHelpFormatter
import envvars
import sys

_A_CONNECT = 'connect'
_A_ERROR = 'unimplemented'

class KalturaArgParser(envvars.ArgumentParser):

    KALTURA_ENV_VARS = { 'partnerId': 'KALTURA_PARTNERID|Kaltura Partner Id|',
                      'secret': 'KALTURA_SECRET|Kaltura Secret to access API|',
                      'userId': 'KALTURA_USERID|Kaltura User Id|'}

    DESCRIPTION = """
         do stuff with Kaltura Admin API

         The script uses the following environment variables
    """


    ACTIONS = [_A_CONNECT, _A_ERROR]

    @staticmethod
    def create(description=DESCRIPTION):

        evars = envvars.to_doc(KalturaArgParser.KALTURA_ENV_VARS)
        for k in evars:
            description = description + "\n\t%-15s:  %s" % (k, evars[k])

        loglevels = ['CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG', 'NOTSET']
        parser = KalturaArgParser(description=description, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("--action", "-a",  choices=KalturaArgParser.ACTIONS, default='connect', help="action to perform")
        parser.add_argument("--loglevel", "-l", choices=loglevels,  default=logging.INFO, help="log level  - default: INFO")

        return parser


def check_env():
    env = envvars.to_value(KalturaArgParser.KALTURA_ENV_VARS)
    for v in env:
        logging.info("%s=%s" % (v, '***' if v == "secret" else env[v]))
    if len(env) < len(KalturaArgParser.KALTURA_ENV_VARS):
        raise RuntimeError("Missing environment variable/s")
    return env



def startsession(partnerId, userId, secret):
    """ Use configuration to generate KS
    """
    config = KalturaConfiguration(partnerId)
    config.serviceUrl = "https://www.kaltura.com/"
    client = KalturaClient(config)
    ktype = KalturaSessionType.ADMIN
    expiry = 432000 # 432000 = 5 days
    privileges = "disableentitlement"

    ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
    client.setKs(ks)
    return client


def main(args):
    print(args)
    if 'loglevel' in args:
        logging.getLogger().setLevel(args['loglevel'])
    args.update(check_env())
    print(args)
    action = args['action']
    if (action == _A_CONNECT):
        cl = startsession(partnerId=args['partnerId'], userId=args['userId'],  secret=args['secret'])
        logging.info(cl)
    else:
        raise RuntimeError("action '%s' not yet implemented" % action)


if __name__ == '__main__':
    parser = KalturaArgParser.create()
    args = parser.parse_args()
    try:
        main(vars(args))
        sys.exit(0)
    except Exception as e:
        print("")
        parser.print_usage()
        #traceback.print_exc()
        sys.exit(1)
