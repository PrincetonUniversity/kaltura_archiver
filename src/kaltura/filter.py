from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

from KalturaClient.Plugins.ElasticSearch import *
import api


class Filter:
	MAX_PAGE_SIZE = 500
	ENTRY_STATUS_READY = KalturaEntryStatus.READY
	ORDER_BY = "+createdAt"  # oldest first
	MEDIA_TYPES = {
		'video' : KalturaMediaType.VIDEO,
		'image' : KalturaMediaType.IMAGE,
		'audio' : KalturaMediaType.AUDIO
	}

	KalturaESearchItem_OPERATOR_STR = {
		KalturaESearchItemType.EXACT_MATCH : "==",
		KalturaESearchItemType.STARTS_WITH : "starts-with",
		KalturaESearchItemType.EXISTS : "exists",
		KalturaESearchItemType.PARTIAL : "~~",
		KalturaESearchItemType.RANGE : ""
	}

	KalturaESearch_OPERATOR_STR = {
		KalturaESearchOperatorType.NOT_OP : "NOT",
		KalturaESearchOperatorType.AND_OP : "AND",
		KalturaESearchOperatorType.OR_OP : "OR"
	}

	def __init__(self, mediaType='video'):
		self.search_params = KalturaESearchEntryParams()
		self.search_params.aggregations = KalturaESearchAggregation()
		self.search_params.searchOperator = KalturaESearchEntryOperator()
		self.search_params.searchOperator.operator = KalturaESearchOperatorType.AND_OP
		self.search_params.searchOperator.searchItems = []
		self._search_for_entry(KalturaESearchEntryFieldName.MEDIA_TYPE,
							   KalturaESearchItemType.EXACT_MATCH,
							   self.MEDIA_TYPES[mediaType])

		self.tag_esearch_entry = None
		#TODO self.filter.orderBy = Filter.ORDER_BY
		self.page  = 1
		self.per_page  = Filter.MAX_PAGE_SIZE
		self.maximum_iter = -1  # no limit

	def first_page(self, page):
		self.page = page
		return self

	def page_size(self, size):
		if (size > Filter.MAX_PAGE_SIZE):
			api.logger.error("Filter.page_size: {} exceeds MAX page size of {}".format(size, Filter.MAX_PAGE_SIZE))
			size = Filter.MAX_PAGE_SIZE
		self.per_page = size
		return self

	def max_iter(self, iter):
		self.maximum_iter = iter
		return self

	def entry_id(self, entryid):
		"""
		filter on entryid being equal

		NOOP if entryid == None

		:param entryid: kaltura media entry id
		:return: self
		"""
		if entryid is not None:
			self._search_for_entry(KalturaESearchEntryFieldName.ID,
								   KalturaESearchItemType.EXACT_MATCH, entryid)
		else:
			api.logger.debug("Filter.entryId: NOOP ")
		return self
    
	def status(self, status):
		"""
		filter on KalturaEntryStatus constant
		:param status:
		:return:
		"""
		if self.filter.statusIn == NotImplemented:
			self.filter.statusIn = str(status)
		else:
			self.filter.statusIn += ",{}".format(status)
		return self

	def tag(self, tag):
		"""
		if tag does not start with '!' match if it (partially) matches kaltura media entry tag

		otherwise reverse matching result

		NOOP if tag == None

		not compatible wih undefined_LAST_PLAYED_AT method

		:param tag: kaltura media entry tag
		:return: self
		"""
		if (tag != None):
			if (self.tag_esearch_entry):
				raise RuntimeError("tag: already defined")


			if tag.startswith("!"):
				search_entry = self._kaltura_search_entry(KalturaESearchEntryFieldName.TAGS,
														  KalturaESearchItemType.PARTIAL,
														  tag[1:])
				# must wrap a NOT operator around tag search_entry
				not_op = KalturaESearchEntryOperator()
				not_op.operator = KalturaESearchOperatorType.NOT_OP
				not_op.searchItems = [search_entry]
				search_entry = not_op
			else:
				search_entry = self._kaltura_search_entry(KalturaESearchEntryFieldName.TAGS,
														  KalturaESearchItemType.PARTIAL,
														  tag)
			self.search_params.searchOperator.searchItems.append(search_entry)
			api.logger.debug('Filter.tag={}'.format(tag))

		return self

	def plays_equal(self, plays):
		if (plays != None):
			if (self.filter.advancedSearch != NotImplemented):
				raise RuntimeError("playsEqual: filter.advancedSearch already defined")
			self.filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
			self.filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.PLAYS
			self.filter.advancedSearch.comparison = KalturaSearchConditionComparison.EQUAL
			self.filter.advancedSearch.value = plays
			api.logger.debug("Filter.playsEqual== {}".format(plays))
		return self

	def category(self, categoryId):
		"""
		match if given categoryId is in a media entrys' category id list

		NOOP if categoryId == None

		:param categoryId: kaltura media entry category id
		:return: self
		"""
		if (categoryId != None):
			self.filter.categoryAncestorIdIn = categoryId
			api.logger.debug("Filter.category={}".format(self.filter.categoryAncestorIdIn))
		return self

	def years_since_played(self, years):
		return self._since_range(KalturaESearchEntryFieldName.LAST_PLAYED_AT, 'lessThanOrEqual', years)

	def played_within_years(self, years):
		return self._since_range(KalturaESearchEntryFieldName.LAST_PLAYED_AT, 'greaterThan', years)

	def years_since_created(self, years):
		return self._since_range(KalturaESearchEntryFieldName.CREATED_AT, 'lessThanOrEqual', years)

	def created_within_years(self, years):
		return self._since_range(KalturaESearchEntryFieldName.CREATED_AT, 'greaterThan', years)


	def get_count(self):
		"""
		return number of records macthing the tag, category, and lastPlayed data

		this ignores the first_page, page_sizem, and max_iter settings
		:return: match count
		"""
		return iter(self).last_results.totalCount

	def _since_range(self, field_name, mode, years):
		"""
		match if video was was not last played since /within the last years

		NOOP if years == None

		:param mode:  lastPlayedAtLessThanOrEqual or lastPlayedAtGreaterThanOrEqual
		:param years: number of years
		:return: self
		"""
		if years is not None:
			range = KalturaESearchRange()
			since = Filter._years_ago(years)
			if (mode == 'lessThanOrEqual'):
				range.lessThanOrEqual = since
			elif (mode == 'greaterThan'):
				range.greaterThan = since
			else:
				raise RuntimeError("mode {} not in [{}, {}]".format(mode, 'lessThanOrEqual', 'greaterThan'))
			self._search_for_entry(field_name, KalturaESearchItemType.RANGE, range)
		else:
			api.logger.debug("Filter.{}{:s}: NOOP".format(field_name, mode))

		return self

	@staticmethod
	def _years_ago(years):
		"""
		:param years: number of years
		:return: return   unix standard time of now() - years

		"""
		d = datetime.now() - relativedelta(years=years)
		return int(calendar.timegm(d.utctimetuple()))

	def __iter__(self):
		return FilterIter(self)

	def _search_for_entry(self, field, op, value):
		search_for = self._kaltura_search_entry(field, op, value)
		self.search_params.searchOperator.searchItems.append(search_for)
		api.logger.debug("Filter + %s" %  self._repr_search_entry_item(search_for))

	@staticmethod
	def _kaltura_search_entry(field, op, value):
		search_for = KalturaESearchEntryItem()  # type: KalturaESearchEntryItem
		search_for.fieldName = field
		search_for.itemType = op
		if op == KalturaESearchItemType.RANGE:
			search_for.range = value
		else:
			search_for.searchTerm = value
		return search_for

	def __str__(self):
		searcher =  self._repr_search_operator(self.search_params.searchOperator)
		return "Filter({}, [page:{} len:{} max={}])".format(searcher, self.page, self.per_page, self.maximum_iter)

	def __repr__(self):
		return str(self)


	@staticmethod
	def _repr_search_operator(search_op):
		op_str = Filter.KalturaESearch_OPERATOR_STR[search_op.operator]
		properties = ""
		for si in search_op.searchItems:
			properties += " [%s]" % Filter._repr_search_entry_item(si)
		return "{}({} )".format(op_str, properties)

	@staticmethod
	def _repr_search_entry_item( search_for):
		if isinstance(search_for, KalturaESearchEntryOperator):
			return Filter._repr_search_operator(search_for)
		op = ""
		value = ""
		if (search_for.itemType != KalturaESearchItemType.RANGE):
			op = Filter.KalturaESearchItem_OPERATOR_STR[search_for.itemType]
			value = search_for.searchTerm
		elif (search_for.range):
			op_value = vars(search_for.range)
			for rop in op_value.keys():
				if op_value[rop] != NotImplemented:
					op +=  "(%s %s) " % (rop, op_value[rop])
		return "%s %s %s" % (str(search_for.fieldName), op, str(value))




class FilterIter:
	def __init__(self, filter):
		self.filter = filter
		self.pager = KalturaPager()
		self.pager.pageSize = filter.per_page
		self.pager.pageIndex = filter.page - 1
		self.max_iter = filter.maximum_iter
		self._next_batch()

	def next(self):
		if (self.max_iter == 0):
			raise StopIteration()
		n = None
		try:
			n = self._next()
		except StopIteration as stp:
			self._next_batch()
			n = self._next()
		api.logger.debug("Filter.next -> %s" % n.getId())
		return n

	def _next_batch(self):
		self.pager.setPageIndex(self.pager.getPageIndex() + 1)
		self.last_results = api.getClient().elasticSearch.eSearch.searchEntry(self.filter.search_params, self.pager)
		if (self.last_results.objects):
			api.logger.debug("%s: iter page %d" % (self.filter, self.pager.getPageIndex()))
			self.object_iter = iter(self.last_results.objects)
		else:
			self.object_iter = iter([])

	def _next(self):
		n = next(self.object_iter)
		self.max_iter -= 1
		return n.object