
import logging, traceback
from argparse import RawDescriptionHelpFormatter
import envvars
import sys
import kaltura

class KalturaArgParser(envvars.ArgumentParser):
    ENV_VARS = {'partnerId': 'KALTURA_PARTNERID|Kaltura Partner Id|',
                        'secret': 'KALTURA_SECRET|Kaltura Secret to access API|',
                        'userId': 'KALTURA_USERID|Kaltura User Id|',
                        'awsAccessKey': 'AWS_ACCESS_KEY_ID|AWS access Key Id|',
                        'awsAccessSecret': 'AWS_SECRET_ACCESS_KEY|AWS secret access key|'}

    DESCRIPTION = """This script interacts with a Kaltura KMC and AWS to list, archive and restore videos to and from AWS storage.

It  uses the following environment variables
"""

    @staticmethod
    def create(description=DESCRIPTION):

        evars = envvars.to_doc(KalturaArgParser.ENV_VARS)
        for k in evars:
            description = description + "\n\t%-15s:  %s" % (k, evars[k])

        loglevels = ['CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG', 'NOTSET']
        parser = KalturaArgParser(description=description, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("--loglevel", "-l", choices=loglevels,  default=logging.INFO, help="log level  - default: INFO")

        subparsers = parser.add_subparsers(help='sub-command help')

        subparsers.add_parser('connect', help='test access to Kaltura KMC and AWS').set_defaults(func=connect)

        subparser = subparsers.add_parser('list', help="list matching videos in Kaltua KMC ")
        subparser.add_argument("--category", "-c",  help="kaltura category")
        subparser.add_argument("--tag", "-t",  help="kaltura tag")
        subparser.add_argument("--unplayed", "-u",  type=int, help="unplayed for given number of years")
        subparser.add_argument("--noLastPlayed", "-n",  action="store_true", default=False, help="undefined LAST_PLAYED_AT attribute")
        subparser.set_defaults(func=list)

        return parser

def connect(params):
    client = kaltura.api.startsession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])
    logging.info(client)

from KalturaClient.Plugins.Core import *

def list(params):

    kaltura.api.startsession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

    filter = kaltura.api.Filter()
    filter.tag(params['tag']).category(params['category']).years_since_played(params['unplayed']);
    if (params['noLastPlayed']) :
            filter.undefined_LAST_PLAYED_AT();
    logging.info("list %s" % str(filter))
    kaltura.api.loop(filter)


def todo(params):
    logging.info("todo %s" % str(params))

def _get_env_vars():
    env = envvars.to_value(KalturaArgParser.ENV_VARS)
    for v in env:
        logging.info("%s=%s" % (v, '***' if "SECRET" in v.upper() else env[v]))
    return env


def _main(args):
    if 'loglevel' in args:
        logging.getLogger().setLevel(args['loglevel'])
    print(args)
    params = _get_env_vars()
    params.update(args)
    print(params)
    params['func'](params)

if __name__ == '__main__':
    parser = KalturaArgParser.create()
    try:
        args = parser.parse_args()
        _main(vars(args))
        sys.exit(0)
    except Exception as e:
        print("\n" + str(e) + "\n")
        parser.print_usage()
        if (not isinstance(e, RuntimeError)):
            traceback.print_exc()
        sys.exit(-1)