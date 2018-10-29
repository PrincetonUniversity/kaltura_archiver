import api
import logging
import urllib
import os

from KalturaClient.Plugins.Core import KalturaMediaEntry, KalturaFlavorAsset, KalturaUploadToken, KalturaUploadedFileTokenResource, KalturaFlavorAssetStatus

ENTRY_ID = 'entry_id'
FLAVOR_ID = 'flavor_id'
LAST_PLAYED = 'last_played'
LAST_PLAYED_DATE = 'last_played_date'
VIEWS = 'views'
ORIGINAL = 'original'
ORIGINAL_STATUS = 'orig_status'
ORIGINAL_SIZE = 'orig_KB'
TOTAL_SIZE = 'total_KB'
SIZE = 'size_KB'
TAGS = 'tags'
CATEGORIES = 'categories'
CATEGORIES_IDS = 'category_ids'
NAME = 'name'
STATUS = 'status'
CREATED_AT = 'created'
CREATED_AT_DATE = 'created_date'
DELETED_AT = 'deleted'
DELETED_AT_DATE = 'deleted_date'
CREATOR_ID = 'creator_id'

class MediaEntry:

    def __init__(self, entry):
        if (not isinstance(entry, KalturaMediaEntry)):
            raise RuntimeError("Can't create MediaEntry with {} instance".format(entry))
        self.entry = entry

    def reload(self):
        self.entry = api.getClient().media.get(self.entry.getId())
        return self.entry

    def getTotalSize(self):
        size = 0
        for f in FlavorAssetIterator(self.entry):
            if (f.getSize()):
                size += f.getSize()
        return size

    def getLastPlayedDate(self):
        return api.dateString(self.entry.getLastPlayedAt())

    def getOriginalFlavor(self):
        """
        :return: original flavor or None
        """
        for f in FlavorAssetIterator(self.entry):
            if (f.getIsOriginal()):
                return f
        return None

    def downloadOriginal(self, tmp, doit=False):
        """
        download original flavor to file in tmp directory

        use the entry id as file name

        if not doit - just log actions - but do not perform

        :param doit: if False only log activity
        :param tmp:  directory path
        :return: upon success return the tenp file name  - otherwise return None
        :raises RuntimeError if the download fails for unexpected reason
        """
        original = self.getOriginalFlavor()
        if (original):
            to_file = "{}/{}.mp4".format(tmp, self.entry.getId())
            download_url = api.getClient().flavorAsset.getUrl(original.getId())
            self.log_action(logging.INFO,doit, "Download", "Flavor({}) to {}".format(Flavor(original), to_file))
            if doit:
                try:
                    urllib.urlretrieve(download_url, to_file)
                    return to_file
                except Exception as e:
                    self.log_action(logging.ERROR,doit, "Failed Download", "Original {} - {}".format(original, e))
                    self.log_action(logging.ERROR,doit, "Delete", to_file) 
                    os.remove(to_file) 
                    return None
            else:
                # dryRun always succeeds
                return to_file
        else:
            self.log_action(logging.ERROR,doit, "Can't Download", "Entry has no ORIGINAL Flavor")
        return None

    def deleteFlavors(self, doDelete=False):
        """
        delete derived flavors  if doDelete
        otherwise simply log actions but do not actually take them

        skip deletion if entry has no original flavor

        :param doDelete: if False only log action take
        :return: False if entry has no ORIGINAL flavor
        """
        for f in FlavorAssetIterator(self.entry):
                if (not Flavor(f).delete(doDelete)):
                    return False
        return True

    def replaceOriginal(self, filepath, doReplace):
        """
        if doReplace then replace original video with contents of given filepath

        :param filepath:  name of file that contains a video
        :param doReplace: if False only log action take
        :return:
        """
        self.log_action(logging.INFO, doReplace, 'Replace original', "with '{}'".format(filepath))
        try:
            if (doReplace):
                uploadToken = KalturaUploadToken()
                client = api.getClient()
                uploadToken = client.uploadToken.add(uploadToken)
                ulfile = file(filepath)
                client.uploadToken.upload(uploadToken.id, ulfile)
                uploadedFileTokenResource = KalturaUploadedFileTokenResource()
                uploadedFileTokenResource.token = uploadToken.id
                client.media.addContent(self.entry.getId(), uploadedFileTokenResource)
                client.media.updateThumbnail(self.entry.getId(), 1)
            return True
        except Exception as e:
            self.log_action(logging.ERROR, doReplace, "Replace Orig", str(e))
            return False

    def addTag(self, newtag, doUpdate=False):
        """
        add given tag to entry
        :param newtag: tag string
        :param doUpdate: if False only log action take
        :return: None
        """
        mediaEntry = KalturaMediaEntry()
        mediaEntry.tags = self.entry.getTags() + ", " + newtag
        self.log_action(logging.INFO, doUpdate, 'Add Tag', newtag)
        if doUpdate:
            api.getClient().media.update(self.entry.getId(), mediaEntry)
        return None

    def delTag(self, remove_tag, doUpdate=False):
        mediaEntry = KalturaMediaEntry()
        tags = self.entry.tags.split(', ')
        tags.remove(remove_tag)
        mediaEntry.tags = ",".join(tags)
        self.log_action(logging.INFO, doUpdate, 'Del Tag', remove_tag)
        if doUpdate:
            api.getClient().media.update(self.entry.getId(), mediaEntry)
        return None


    def report_str(self, column):
        if column == ENTRY_ID:
            return self.entry.getId()
        if column ==  LAST_PLAYED_DATE:
            return "{:>10}".format(api.dateString(self.entry.getLastPlayedAt()))
        if column == LAST_PLAYED:
            return "{:>12}".format(self.entry.getLastPlayedAt())
        if column == CREATED_AT_DATE:
            return "{:>10}".format(api.dateString(self.entry.getCreatedAt()))
        if column == CREATED_AT:
            return "{:>12}".format(self.entry.getCreatedAt())
        if column == VIEWS:
            return str(self.entry.getViews())
        if column == TOTAL_SIZE:
            return "{:>10}".format(self.getTotalSize())
        if column == NAME:
            return self.entry.getName().encode('utf-8')
        if column == TAGS:
            return self.entry.getTags().encode('utf-8')
        if column == CATEGORIES:
            return self.entry.getCategories().encode('utf-8')
        if column == CATEGORIES_IDS:
            return '{:>15}'.format(self.entry.getCategoriesIds().encode('utf-8'))
        original = self.getOriginalFlavor()
        if column == ORIGINAL:
            return '{:>10}'.format(original.getId() if original else  '')
        if column == ORIGINAL_STATUS:
            return (FlavorAssetStatus.str(original.getStatus()) if original else 'MISSING').rjust(len(ORIGINAL_STATUS))
        if column == ORIGINAL_SIZE:
            return "{:>10}".format(original.getSize() if original else '')
        if column == CREATOR_ID:
            return "{:>8}".format(self.entry.creatorId)

        has_tag = column in self.entry.getTags()
        return column if has_tag else ''.ljust(len(column))


    def log_action(self, log_level, doIt, action, message):
        api.log_action(log_level, doIt,'Entry', self.entry.getId(), action, message)


class Flavor:
    def __init__(self, flavor):
        if (not isinstance(flavor, KalturaFlavorAsset)):
            raise RuntimeError("Can't create Flavor with {} instance".format(flavor))
        self.flavor = flavor

    def isReady(self):
        return self.flavor.getStatus().value == KalturaFlavorAssetStatus.READY

    def delete(self, doDelete):
        self.log_action(logging.INFO, doDelete, "Delete", "")
        if (doDelete):
            api.getClient().flavorAsset.delete(self.flavor.getId())
        return True

    def log_action(self, level, doIt, action, message):
        return api.log_action(level, doIt, 'Entry', self.flavor.getEntryId(), action, "{} {}".format(Flavor(self.flavor), message))


    def report_str(self, column):
        if column ==  FLAVOR_ID:
            return  self.flavor.getId()
        if column ==  ENTRY_ID:
            return  self.flavor.getEntryId()
        if column ==  ORIGINAL:
            return str(self.flavor.getIsOriginal())
        if column == CREATED_AT:
            return "{:>12}".format(self.flavor.getCreatedAt())
        if column == DELETED_AT:
            return str(self.flavor.getDeletedAt())
        if column == DELETED_AT_DATE:
            return "{:>10}".format(api.dateString(self.flavor.getDeletedAt()))
        if column == SIZE:
            return "{:>10}".format(self.flavor.getSize())
        if column == STATUS:
            return FlavorAssetStatus.str(self.flavor.getStatus())
        return 'UNDEFINED'

    def __repr__(self):
        f = self.flavor
        return "Flavor({}, entryId:{}, id:{}, size:{})".format(('Original' if f.getIsOriginal() else 'Derived '),
                                                              f.getEntryId(), f.getId(), f.getSize())


class FlavorAssetIterator:
    def __init__(self, entry):
        self.entry = entry
        self.flavorassetswparamslist = iter(api.getClient().flavorAsset.getFlavorAssetsWithParams(self.entry.id))

    def __iter__(self):
        return self

    def next(self):
        nxt = next(self.flavorassetswparamslist)
        if (nxt.getFlavorAsset() != None):
            return nxt.getFlavorAsset();
        return self.next()


class FlavorAssetStatus:
    """
    based on KalturaFlavorAssetStatus
    """
    _STRINGS = [
        "ERROR",
        "QUEUED",
        "CONVERTING",
        "READY",
        "DELETED",
        "NOT_APPLICABLE",
        "TEMP",
        "WAIT_FOR_CONVERT",
        "IMPORTING",
        "VALIDATING",
        "EXPORTING"
    ]

    @staticmethod
    def str(status):
        return FlavorAssetStatus._STRINGS[status.value + 1]
