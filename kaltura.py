#!/usr/bin/env python 
import logging, traceback
import os
import boto3
from argparse import RawDescriptionHelpFormatter
import envvars
import sys

import kaltura

class KalturaArgParser(envvars.ArgumentParser):
    ENV_VARS = {'partnerId': 'KALTURA_PARTNERID|Kaltura Partner Id|',
                        'secret': 'KALTURA_SECRET|Kaltura secret to access API|',
                        'userId': 'KALTURA_USERID|Kaltura user Id|',
                        'awsAccessKey': 'AWS_ACCESS_KEY_ID|AWS access Key Id|',
                        'awsAccessSecret': 'AWS_SECRET_ACCESS_KEY|AWS secret access key|',
                        'awsBucket' : 'AWS_BUCKET|AWS s3 bucket for video storage|',
                        'videoPlaceholder' : 'PLACEHOLDER_VIDEO|placeholder video|placeholder_video.mp4'}

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

        subparsers.add_parser('check_config', help='test access to Kaltura KMC, AWS ....').set_defaults(func=setup)

        subparser = subparsers.add_parser('list', help="list matching videos in Kaltua KMC ")
        subparser.add_argument("--mode", "-m", choices=["video", "flavor"], default="video", help="list video or falvor information")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=list)

        return parser

    @staticmethod
    def _add_filter_parsm(subparser):
        subparser.add_argument("--category", "-c",  help="kaltura category")
        subparser.add_argument("--tag", "-t",  help="kaltura tag")
        subparser.add_argument("--id", "-i",  help="kaltura media entry id")
        subparser.add_argument("--unplayed", "-u",  type=int, help="unplayed for given number of years")
        subparser.add_argument("--played", "-p",  type=int, help="played within the the given number of years")
        subparser.add_argument("--noLastPlayed", "-n",  action="store_true", default=False, help="undefined LAST_PLAYED_AT attribute")
        return None


def list(params):
    """
    print matching kaltura records

    run kaltura.py list --help to get a list of available searcj filter options

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    mode = params['mode']
    logging.info("list {} {}".format(mode, filter))

    if (params['mode'] == 'video'):
        columns = ['lastPlayedDate', 'lastPlayedAt', 'views', 'id', 'categories', 'categoriesIds', 'tags']
        print('\t'.join(columns))
        for entry in filter:
            print kaltura.MediaEntry.join("\t", entry, columns)
    else:
        for entry in filter:
            print(entry.id)
            for f in kaltura.FlavorAssetIterator(entry):
                print("\t".join([str(entry.id), f.__class__str(f.id), str(f.getIsOriginal()),  str(vars(f))]))
    return None


def _create_filter(params):
    filter = kaltura.Filter()
    filter.entry_id(params['id']).tag(params['tag']).category(params['category'])
    filter.years_since_played(params['unplayed']).played_within_years(params['played'])
    if (params['noLastPlayed']) :
        filter.undefined_LAST_PLAYED_AT();
    return filter

def setup(params):
    # connect to Kaltura
    kaltura.api.startsession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

    # Check for existence of placeholder video
    if not os.path.isfile(params['videoPlaceholder']):
        raise(RuntimeError("Can not access placeholder file '{}'".format(params['videoPlaceholder'])))
    else:
        logging.info("setup: videoPlaceholder={}".format(params['videoPlaceholder']))

    # chek on AWS bucket
    bucket = params['awsBucket']
    try:
        s3resource = boto3.resource('s3')
        s3resource.meta.client.head_bucket(Bucket=bucket)
        logging.info("Using AWS bucket {}".format(bucket))
    except Exception as e:
        raise(RuntimeError("Can't access AWS Bucket '{}'".format(bucket)))




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
    logging.info(args)
    params = _get_env_vars()
    params.update(args)
    #print(params)
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
