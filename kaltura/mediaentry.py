import api
import logging
from KalturaClient.Plugins.Core import KalturaMediaEntry, KalturaFlavorAsset

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

    def deleteDerivedFlavors(self, doDelete=False):
        for f in FlavorAssetIterator(self.entry):
            if (f.getIsOriginal()):
                logging.info("{} Skip   Flavor: {}".format(self._log(doDelete), Flavor(f)))
            else:
                logging.info("{} Delete Flavor: {}".format(self._log(doDelete), Flavor(f)))
                if (doDelete):
                    api.getClient().flavorAsset.delete(f.getId())


    def addTag(self, newtag, doUpdate=False):
        """
        add given tag to entry
        :param newtag: tag string
        :param doUpdate: if False only fo through the motions
        :return:
        """
        mediaEntry = KalturaMediaEntry()
        mediaEntry.tags = self.entry.tags + ", " + newtag
        logging.info("{} Tag    {} -> {}".format(self._log(doUpdate), self.entry.tags, mediaEntry.tags))
        if doUpdate:
            api.getClient().media.update(self.entry.getId(), mediaEntry)

    def _log(self, doIt):
        return "Entry {}{} | ".format(self.entry.getId(), '' if doIt else ' DRYRUN')

class Flavor:
    def __init__(self, flavor):
        if (not isinstance(flavor, KalturaFlavorAsset)):
            raise RuntimeError("Can't create MediaEntry with {} instance".format(flavor))
        self.flavor = flavor

    def __repr__(self):
        f = self.flavor
        return "entryId:{}, id:{}, {}, size:{}".format(f.getEntryId(), f.getId(), ('ORIGINAL' if f.getIsOriginal() else 'derived'), f.getSize())


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
