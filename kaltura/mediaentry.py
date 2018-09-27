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

    def getOriginalFlavor(self):
        """
        :return: original flavor or None
        """
        for f in FlavorAssetIterator(self.entry):
            if (f.getIsOriginal()):
                return f
        return None

    def deleteDerivedFlavors(self, doDelete=False):
        """
        delete derived flavors  if doDelete
        otherwise simply log actions but do not actually take them

        skip deletion if entry has no original flavor

        :param doDelete: actually delete flavors
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
            logging.info("{} Skip   Flavor: {}".format(self._log(doDelete), Flavor(original)))
            for f in derived:
                Flavor(f).delete(doDelete)
            return True
        else:
            logging.error("{} Skip   Entry: {} has no ORIGINAL flavor".format(self._log(doDelete), self.entry.getId()))
        return False

    def addTag(self, newtag, doUpdate=False):
        """
        add given tag to entry
        :param newtag: tag string
        :param doUpdate: if False only go through the motions
        :return: None
        """
        mediaEntry = KalturaMediaEntry()
        mediaEntry.tags = self.entry.tags + ", " + newtag
        logging.info("{} Tag    '{}' -> '{}'".format(self._log(doUpdate), self.entry.tags, mediaEntry.tags))
        if doUpdate:
            api.getClient().media.update(self.entry.getId(), mediaEntry)
        return None

    def _log(self, doIt):
        return "Entry {}{} | ".format(self.entry.getId(), '' if doIt else ' DRYRUN')

class Flavor:
    def __init__(self, flavor):
        if (not isinstance(flavor, KalturaFlavorAsset)):
            raise RuntimeError("Can't create Flavor with {} instance".format(flavor))
        self.flavor = flavor

    def delete(self, doDelete):
        logging.info("{} Delete Flavor: {}".format(self._log(doDelete), self))
        if (doDelete):
            api.getClient().flavorAsset.delete(self.flavor.getId())

    def _log(self, doIt):
        return "Entry {}{} | ".format(self.flavor.getEntryId(), '' if doIt else ' DRYRUN')

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
