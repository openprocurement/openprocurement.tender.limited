# -*- coding: utf-8 -*-
import unittest
from openprocurement.tender.limited.tests.base import test_tender_data, BaseTenderWebTest

test_tender_data_mode_test = test_tender_data.copy()
test_tender_data_mode_test["mode"] = "test"


class AccreditationTenderTest(BaseTenderWebTest):
    def test_create_tender_accreditation(self):
        for broker in ['broker1', 'broker3']:
            self.app.authorization = ('Basic', (broker, ''))
            response = self.app.post_json('/tenders', {"data": test_tender_data})
            self.assertEqual(response.status, '201 Created')
            self.assertEqual(response.content_type, 'application/json')

        for broker in ['broker2', 'broker4']:
            self.app.authorization = ('Basic', (broker, ''))
            response = self.app.post_json('/tenders', {"data": test_tender_data}, status=403)
            self.assertEqual(response.status, '403 Forbidden')
            self.assertEqual(response.content_type, 'application/json')
            self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit tender creation")

        self.app.authorization = ('Basic', ('broker1t', ''))
        response = self.app.post_json('/tenders', {"data": test_tender_data}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Broker Accreditation level does not permit tender creation")

        response = self.app.post_json('/tenders', {"data": test_tender_data_mode_test})
        self.assertEqual(response.status, '201 Created')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AccreditationTenderTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
