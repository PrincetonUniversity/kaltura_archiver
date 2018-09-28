#!/usr/bin/env python 
import logging, traceback
import os
import boto3
from argparse import RawDescriptionHelpFormatter
import envvars
import sys

import kaltura
import kaltura.aws as aws

FLAVORS_DELETED_TAG = "flavors_deleted"
SAVED_TO_S3 = "archived_to_s3"

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

        subparsers.add_parser('config', help='test access to Kaltura KMC, AWS ....').set_defaults(func=setup)

        subparser = subparsers.add_parser('list', help="list matching videos in Kaltua KMC ")
        subparser.add_argument("--mode", "-m", choices=["video", "flavor"], default="video", help="list video or falvor information")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=list)

        subparser = subparsers.add_parser('del_flavors', help="delete derived flavors of matching videos in Kaltura KMC ")
        subparser.add_argument("--delete", action="store_true", default=False, help="performs in dryrun mode, unless delete param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=del_flavors)

        subparser = subparsers.add_parser('archive', help="archive original flavors of matching videos in Kaltura KMC ")
        subparser.add_argument("--save", action="store_true", default=False, help="performs in dryrun mode, unless save param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=save_to_aws)

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

def save_to_aws(params):
    """
    save original flavors to aws  for  matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    doit = params['save']
    logging.info("save_to_aws save={} {}".format(doit, filter))

    failed_save = []
    no_orig = []
    for entry in filter:
        mentry = kaltura.MediaEntry(entry)
        original = mentry.getOriginalFlavor()
        if (original):
            fname = mentry.downloadOriginal(doit)
            if (fname):
                aws.s3_store(fname, params['awsBucket'], entry.getId(), doit)
                kaltura.MediaEntry(entry).addTag(SAVED_TO_S3)
            else:
                failed_save.append(entry)
        else:
            no_orig.append(entry)

    if (failed_save):
        logging.error("FAILED to save original for {}".format(",".join(e.getId() for e in failed_save)))
    if (no_orig):
        logging.warn("Entries without original flavor: {}".format(",".join(e.getId() for e in no_orig)))
    return None


def del_flavors(params):
    """
    delete derived flavors from  matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    doit = params['delete']
    logging.info("del_flavors delete={} {}".format(doit, filter))

    failed = []
    for entry in filter:
        mentry = kaltura.MediaEntry(entry)
        if (mentry.deleteDerivedFlavors(doDelete=doit)):
            mentry.addTag(FLAVORS_DELETED_TAG, doit)
        else:
            failed.append(entry)
    if (failed):
        logging.error("FAILED to delete flavors from {}".format(",".join(e.getId() for e in failed)))
    return None

def list(params):
    """
    print matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    mode = params['mode']
    logging.info("list {} {}".format(mode, filter))

    if (params['mode'] == 'video'):
        columns = ['lastPlayedDate', 'lastPlayedAt', 'views', 'id', 'totalSize', 'categories', 'categoriesIds', '|', 'tags', '|',  'name']
        print('\t'.join(columns))
        for entry in filter:
            kentry = kaltura.MediaEntry(entry)
            s = ""
            s += "{:>10}\t".format(kentry.getLastPlayedDate())
            s += "{:>12}\t".format(entry.getLastPlayedAt())
            s += "{}\t".format(entry.getViews())
            s += "{:>12}\t".format(entry.getId())
            s += "{:>10}\t".format(kentry.getTotalSize())
            s += "{:.15}\t".format(entry.getCategories())
            s += "{}\t".format(entry.getCategoriesIds())
            s += "|\t"
            s += "{}\t".format(entry.getTags())
            s += "|\t"
            s += "{}\t".format(entry.getName())
            print s
    else:
        columns = ['id', 'flavor-id', 'original', 'size(KB)', 'createdAt', 'createdAtDate', 'deletedAt', 'deletedAtDate', 'status', 'status']
        print('\t'.join(columns))
        for entry in filter:
            for f in kaltura.FlavorAssetIterator(entry):
                s = ""
                s += "{}\t".format(entry.getId())
                s += "{}\t".format(f.getId())
                s += "{}\t".format(f.getIsOriginal())
                s += "{:>10}\t".format(f.getSize())
                s += "{:>12}\t".format(f.getCreatedAt())
                s += "{:>10}\t".format(kaltura.dateString(f.getCreatedAt()))
                s += "{:>12}\t".format(f.getDeletedAt())
                s += "{:>10}\t".format(kaltura.dateString(f.getDeletedAt()))
                s += "{}\t".format(f.getStatus().value)
                s += "{}\t".format(kaltura.FlavorAssetStatus.str(f.getStatus()))
                print(s)
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
    kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

    # Check for existence of placeholder video
    if not os.path.isfile(params['videoPlaceholder']):
        raise(RuntimeError("Can not access placeholder file '{}'".format(params['videoPlaceholder'])))
    else:
        logging.info("setup: videoPlaceholder={}".format(params['videoPlaceholder']))
    print(params)

    # check on AWS bucket
    bucket = params['awsBucket']
    try:
        s3resource = boto3.resource('s3')
        s3resource.meta.client.head_bucket(Bucket=bucket)
        logging.info("Using AWS bucket {}".format(bucket))
    except Exception as e:
        raise(RuntimeError("Can't access AWS Bucket '{}'".format(bucket)))


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
