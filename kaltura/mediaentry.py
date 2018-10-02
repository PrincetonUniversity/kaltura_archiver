import api
import logging
import tempfile
import urllib

from KalturaClient.Plugins.Core import KalturaMediaEntry, KalturaFlavorAsset, KalturaUploadToken, KalturaUploadedFileTokenResource, KalturaFlavorAssetStatus


class MediaEntry:
    def __init__(self, entry):
        if (not isinstance(entry, KalturaMediaEntry)):
            raise RuntimeError("Can't create MediaEntry with {} instance".format(entry))
        self.entry = entry

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

    def downloadOriginal(self, doit=False):
        """
        generate a temporary file name and download the original flavor file

        if not doit - just log actions - but do not perform

        :param if False only log action take
        :return: upon success return the tenp file name  - otherwise return None
        """
        original = self.getOriginalFlavor()
        if (original):
            to_file = tempfile.mkstemp()[1]
            download_url = api.getClient().flavorAsset.getUrl(original.getId())
            self.log_action(logging.INFO,doit, "Download", "Flavor({}) to {}".format(Flavor(original), to_file))
            if doit:
                try:
                    urllib.urlretrieve(download_url, to_file)
                    return to_file
                except Exception as e:
                    self.log_action(logging.ERROR,doit, "Failed Download", "Original {} - {}".format(original, e))
            else:
                # dryRun always succeeds
                return to_file
        else:
            self.log_action(logging.ERROR,doit, "Can't Download", "Entry has no ORIGINAL Flavor")
        return None

    def deleteDerivedFlavors(self, doDelete=False):
        """
        delete derived flavors  if doDelete
        otherwise simply log actions but do not actually take them

        skip deletion if entry has no original flavor

        :param doDelete: if False only log action take
        :return: False if entry has no ORIGINAL flavor
        """
        derived = []
        original = None
        for f in FlavorAssetIterator(self.entry):
            if (f.getIsOriginal()):
                original = f
            else:
                derived.append(f)

        if (original != None):
            for f in derived:
                Flavor(f).delete(doDelete)
            return True
        else:
            self.log_action(logging.ERROR, doDelete, "Abort Delete", "Entry has no ORIGINAL Flavor")
        return False

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
        mediaEntry.tags = self.entry.tags + ", " + newtag
        self.log_action(logging.INFO, doUpdate, 'Add Tag', "'{}' -> '{}'".format(self.entry.tags, mediaEntry.tags))
        if doUpdate:
            api.getClient().media.update(self.entry.getId(), mediaEntry)
        return None

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

    def log_action(self, level, doIt, action, message):
        return api.log_action(level, doIt, 'Entry', self.flavor.getEntryId(), action, "{} {}".format(Flavor(self.flavor), message))

    def __repr__(self):
        f = self.flavor
        return "entryId:{}, id:{}, {}, size:{}".format(f.getEntryId(), f.getId(),
                                                       ('ORIGINAL' if f.getIsOriginal() else 'derived'), f.getSize())


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
