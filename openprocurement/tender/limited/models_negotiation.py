from datetime import timedelta
from zope.interface import implementer
from schematics.exceptions import ValidationError
from schematics.types import StringType
from schematics.types.compound import ModelType
from openprocurement.api.models import ITender, Period, IsoDateTimeType, get_now
from openprocurement.tender.limited.models import Tender as BaseTender
TENDER_STAND_STILL_DAYS = 1
TENDER_PERIOD = timedelta(days=TENDER_STAND_STILL_DAYS)


class PeriodStartEndRequired(Period):
    startDate = IsoDateTimeType(required=True, default=get_now)  # The state date for the period.
    endDate = IsoDateTimeType(required=True, default=get_now)  # The end date for the period.


@implementer(ITender)
class Tender(BaseTender):
    """ Negotiation """
    procurementMethodType = StringType(default="negotiation")
    tenderPeriod = ModelType(PeriodStartEndRequired, required=True)  # The period when the tender is open for submissions. The end date is the closing date for tender submissions.

    def validate_tenderPeriod(self, data, period):
        if period and period.startDate + TENDER_PERIOD > period.endDate:
            raise ValidationError(u"tenderPeriod should be greater than {} days".format(TENDER_STAND_STILL_DAYS))
