import unittest
from openprocurement.tender.limited.adapters import (TenderNegotiationConfigurator,
                                                     TenderReportingConfigurator,
                                                     TenderNegotiationQuickConfigurator,
                                                     )


class ConfiguratorValueTest(unittest.TestCase):

    def test_reverse_awarding_criteria(self):
        self.assertEqual(TenderNegotiationConfigurator.reverse_awarding_criteria, False)
        self.assertEqual(TenderNegotiationQuickConfigurator.reverse_awarding_criteria, False)
        self.assertEqual(TenderReportingConfigurator.reverse_awarding_criteria, False)

    def test_awarding_criteria_key(self):
        self.assertEqual(TenderNegotiationConfigurator.awarding_criteria_key, 'amountPerfomance')
        self.assertEqual(TenderNegotiationQuickConfigurator.awarding_criteria_key, 'amountPerfomance')
        self.assertEqual(TenderReportingConfigurator.awarding_criteria_key, 'amountPerfomance')


def suite():
    current_suite = unittest.TestSuite()
    current_suite.addTest(unittest.makeSuite(ConfiguratorValueTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
