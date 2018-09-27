import logging
import boto3
import botocore

_s3 = boto3.resource('s3')


def s3_exists(filename, bucketname):
    """
    :param filename:  file name
    :param bucketname:  name of S3/GLACIER bucket
    :return:  whether filename exists in bucket
    """
    try:
        _s3.Object(bucketname, filename).load()
        return True
    except botocore.exceptions.ClientError as e:
        logging.debug("s3_object_exists({}, {}): {}".format(bucketname, filename, e.response.message))
        return False

def s3_size(filename, bucketname):
    """
    :param filename:  file name
    :param bucketname:  name of S3/GLACIER bucket
    :return:  size in bytes if object exists; otherwise return 0
    """
    try:
        o = _s3.Object(bucketname, filename)
        return o.content_length
    except botocore.exceptions.ClientError as e:
        logging.debug("s3_object_size({}, {}): {}".format(bucketname, filename, e.response.message))
        return 0

def glacier_store(src_file, bucketname, bucketfile, doit=False):
    if (doit):
        _s3.meta.client.upload_file(src_file, bucketname, bucketfile)
    logging.info("File  {}{} | Store   {} to s3://{}/{}".format(bucketfile, _dryrun(doit), src_file, bucketname, bucketfile))
    return None

def glacier_restore(filename, bucketname, doit=False):
    """
    if file is not available in S3,
    issues restore request for the given filename in the given bucket, unless there is a pending request

    that way the file will eventually be restored to S3

    :param filename: filename to restore
    :param bucketname: name of Glacier bucket
    :param doit: unless doit  simply dryRun/log actions
    :return: whether file is available in S3
    """

    # Check current status
    obj = _s3.Object(bucketname, filename)
    storage_class = obj.storage_class
    restore = obj.restore

    print ("Storage class: %s" % storage_class)
    print("Restore status: %s" % restore)

    if obj.storage_class == 'GLACIER':
        if obj.restore is None:
            logging.info("AWS {}{} Restore Request s3://{}/{}".format(_dryrun(doit), obj.storage_class, bucketname, filename))
            if doit:
                bucket = _s3.Bucket(bucketname)
                bucket.meta.client.restore_object(
                    Bucket=bucketname,
                    Key=filename,
                    RestoreRequest={'Days': 2,
                                    'GlacierJobParameters': {'Tier': 'Bulk'}}
                )
        else:
            # assuming S3
            logging.info("AWS {}{} Restore {} s3://{}/{}".format(_dryrun(doit), obj.storage_class, obj.restore, bucketname, filename))
    else:
        logging.info("AWS {}{} Restore to S3 s3://{}/{}".format(_dryrun(doit), obj.storage_class, bucketname, filename))
        return True
    return False


def _dryrun(doit):
    return '' if doit else ' DRYRUN '
