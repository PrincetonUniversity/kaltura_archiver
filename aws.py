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
        logging.debug("s3_object_exists({}, {}): {}".format(bucketname, filename, e))
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
        logging.debug("s3_object_size({}, {}): {}".format(bucketname, filename, e))
        return 0

def s3_store(src_file, bucketname, bucketfile, doit=False):
    if (doit):
        _s3.meta.client.upload_file(src_file, bucketname, bucketfile)
    logging.info("File  {}{} | Store   {} to s3://{}/{}".format(bucketfile, _dryrun(doit), src_file, bucketname, bucketfile))
    return None

def s3_restore(filename, bucketname, doit=False):
    """
    if file's storage indicates that it is in GLACUER issue a restore request unless there is a request already underway

     - calling this method for the first time issues a restore request if necessary
     - on following calls it will simply return false
     - and once file is available for download it returns True

    :param filename: filename to restore
    :param bucketname: name of Glacier bucket
    :param doit: unless doit  simply dryRun/log actions
    :return: whether file is available in S3 ready to be downloaded
    """

    try:
        obj = _s3.Object(bucketname, filename)

        if obj.storage_class == 'GLACIER':
            if str(obj.restore).startswith('ongoing-request="false"'):
                logging.info("File {}{} {:<20} storage-class={} s3://{}/{}".format(filename, _dryrun(doit), 'AWS Request Restore', obj.storage_class, bucketname, filename))
                if doit:
                    bucket = _s3.Bucket(bucketname)
                    bucket.meta.client.restore_object(
                        Bucket=bucketname,
                        Key=filename,
                        RestoreRequest={'Days': 2,
                                        'GlacierJobParameters': {'Tier': 'Bulk'}}
                    )
            else:
                logging.info("File {}{} {:<20} storage-class={} obj.restore={} s3://{}/{}".format(filename, _dryrun(doit), 'AWS Restoring', obj.storage_class, obj.restore, bucketname, filename))
        elif (obj.storage_class == None):
            logging.info("File {}{} {:<20} storage-class={} s3://{}/{}".format(filename, _dryrun(doit), 'AWS Restored', obj.storage_class, bucketname, filename))
            return True
        else:
            logging.error("File {}{} {:<20} storage-class={} s3://{}/{}".format(filename, _dryrun(doit), 'AWS UNKNOWN', obj.storage_class, bucketname, filename))
    except botocore.exceptions.ClientError as e:
        logging.info("File {}{} {:<20} {}".format(filename, _dryrun(doit), "AWS Access", e))

    return False


def _dryrun(doit):
    return '' if doit else ' DRYRUN |'
