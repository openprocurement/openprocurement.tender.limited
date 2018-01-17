import unittest
from openprocurement.tender.core.tests.configurator import ConfiguratorTestMixin
from openprocurement.tender.limited.adapters import (TenderNegotiationConfigurator,
                                                     TenderReportingConfigurator,
                                                     TenderNegotiationQuickConfigurator)
from openprocurement.tender.limited.models import (ReportingTender, NegotiationTender,
                                                   NegotiationQuickTender)


class ConfiguratorTestTenderNegotiationConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderNegotiationConfigurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = NegotiationTender


class ConfiguratorTestTenderReportingConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderReportingConfigurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = ReportingTender


class ConfiguratorTestTenderNegotiationQuickConfigurator(unittest.TestCase, ConfiguratorTestMixin):
    configurator_class = TenderNegotiationQuickConfigurator
    reverse_awarding_criteria = False
    awarding_criteria_key = 'not yet implemented'
    configurator_model = NegotiationQuickTender


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderNegotiationConfigurator))
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderReportingConfigurator))
    suite.addTest(unittest.makeSuite(ConfiguratorTestTenderNegotiationQuickConfigurator))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
