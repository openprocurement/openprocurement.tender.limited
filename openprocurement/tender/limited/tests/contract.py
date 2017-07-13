# -*- coding: utf-8 -*-
import unittest

import time
from iso8601 import parse_date
from datetime import timedelta
from copy import deepcopy
from uuid import uuid4

from openprocurement.api.tests.base import test_bids
from openprocurement.api.models import get_now, SANDBOX_MODE
from openprocurement.tender.limited.tests.base import (
    BaseTenderContentWebTest, test_tender_data, test_tender_negotiation_data,
    test_tender_negotiation_quick_data, test_organization, test_lots)


class TenderContractResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_data = test_tender_data
    initial_bids = None  # test_bids

    def create_award(self):
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending',
                                                          'qualified': True, 'value': {"amount": 469,
                                                                                       "currency": "UAH",
                                                                                       "valueAddedTaxIncluded": True}}})
        award = response.json['data']
        self.award_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "active"}})

    def setUp(self):
        super(TenderContractResourceTest, self).setUp()
        self.create_award()

    def test_create_tender_contract_invalid(self):
        # This can not be, but just in case check
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/some_id/contracts',
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award_id}},
                                      status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'tender_id'}
        ])

        request_path = '/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token)

        response = self.app.post(request_path, 'data', status=415)
        self.assertEqual(response.status, '415 Unsupported Media Type')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description':
                u"Content-Type header should be one of ['application/json']",
             u'location': u'header',
             u'name': u'Content-Type'}
        ])

        response = self.app.post(
            request_path, 'data', content_type='application/json', status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'No JSON object could be decoded',
                u'location': u'body', u'name': u'data'}
        ])

        response = self.app.post_json(request_path, 'data', status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Data not available',
                u'location': u'body', u'name': u'data'}
        ])

        response = self.app.post_json(
            request_path, {'not_data': {}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Data not available',
                u'location': u'body', u'name': u'data'}
        ])

        response = self.app.post_json(request_path, {'data': {
                                      'invalid_field': 'invalid_value'}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Rogue field', u'location':
                u'body', u'name': u'invalid_field'}
        ])

        response = self.app.post_json(request_path, {'data': {'awardID': 'invalid_value'}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'awardID should be one of awards'], u'location': u'body', u'name': u'awardID'}
        ])

    def test_create_tender_contract_with_token(self):
        # This can not be, but just in case check
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/tenders/{}/contracts'.format(self.tender_id),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award_id}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        contract = response.json['data']
        self.assertIn('id', contract)
        self.assertIn(contract['id'], response.headers['Location'])

        response = self.app.patch_json('/tenders/{}/contracts/{}'.format(self.tender_id, contract['id']),
                                       {"data": {"status": "terminated"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "terminated")

        response = self.app.patch_json('/tenders/{}/contracts/{}'.format(self.tender_id, contract['id']),
                                       {"data": {"status": "pending"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update contract status")

        tender = self.db.get(self.tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # works for negotiation tender
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, contract['id'], self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'complete')

        response = self.app.post_json('/tenders/{}/contracts'.format(self.tender_id),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')

    def test_create_tender_contract(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract_id = response.json['data'][0]['id']

        response = self.app.post_json('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')

        # at next steps we test to create contract in 'complete' tender status
        # time travel
        tender = self.db.get(self.tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'complete')

        response = self.app.post_json('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # at next steps we test to create contract in 'cancelled' tender status
        response = self.app.post_json('/tenders?acc_token={}',
                                      {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender_id = response.json['data']['id']
        tender_token = response.json['access']['token']

        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
            tender_id, tender_token), {'data': {'reason': 'cancellation reason', 'status': 'active'}})
        self.assertEqual(response.status, '201 Created')

        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'cancelled')

        response = self.app.post_json('/tenders/{}/contracts?acc_token={}'.format(tender_id, tender_token),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')

    def test_patch_tender_contract(self):
        response = self.app.get('/tenders/{}/contracts'.format(
                self.tender_id))
        self.contract_id = response.json['data'][0]['id']

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"value": {"currency": "USD"}}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Can\'t update currency for contract value")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"value": {"valueAddedTaxIncluded": False}}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can\'t update valueAddedTaxIncluded for contract value")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"value": {"amount": 501}}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Value amount should be less or equal to awarded amount (469.0)")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"value": {"amount": 238}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['value']['amount'], 238)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
                                       {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")
        self.assertIn("dateSigned", response.json['data'])

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "cancelled"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (complete) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "pending"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (complete) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (complete) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"awardID": "894917dc8b1244b6aab9ab0ad8c8f48a"}},
            status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')

        # at next steps we test to patch contract in 'cancelled' tender status
        response = self.app.post_json('/tenders?acc_token={}',
                                      {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender_id = response.json['data']['id']
        tender_token = response.json['access']['token']

        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, tender_token),
                                      {'data': {'suppliers': [test_organization], 'status': 'pending'}})
        award_id = response.json['data']['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, tender_token),
                                       {"data": {'qualified': True, "status": "active"}})

        response = self.app.get('/tenders/{}/contracts'.format(tender_id))
        contract_id = response.json['data'][0]['id']

        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, tender_token),
                                      {'data': {'reason': 'cancellation reason', 'status': 'active'}})
        self.assertEqual(response.status, '201 Created')

        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'cancelled')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            tender_id, contract_id, tender_token),
            {"data": {"awardID": "894917dc8b1244b6aab9ab0ad8c8f48a"}},
            status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            tender_id, contract_id, tender_token), {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (cancelled) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/some_id?acc_token={}'.format(
            self.tender_id, self.tender_token), {"data": {"status": "active"}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.patch_json('/tenders/some_id/contracts/some_id', {"data": {"status": "active"}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.get('/tenders/{}/contracts/{}'.format(self.tender_id, self.contract_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")
        self.assertEqual(response.json['data']["value"]['amount'], 238)

    def test_tender_contract_signature_date(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.assertNotIn("dateSigned", response.json['data'][0])
        self.contract_id = response.json['data'][0]['id']

        one_hour_in_furure = (get_now() + timedelta(hours=1)).isoformat()
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"dateSigned": one_hour_in_furure}},
            status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'],
                         [{u'description': [u"Contract signature date can't be in the future"],
                           u'location': u'body',
                           u'name': u'dateSigned'}])

        custom_signature_date = get_now().isoformat()
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"dateSigned": custom_signature_date}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")
        self.assertEqual(response.json['data']["dateSigned"], custom_signature_date)
        self.assertIn("dateSigned", response.json['data'])

    def test_get_tender_contract(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract_id = response.json['data'][0]['id']

        response = self.app.get('/tenders/{}/contracts/some_id'.format(self.tender_id), status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.get('/tenders/some_id/contracts/some_id', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

    def test_get_tender_contracts(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.get('/tenders/some_id/contracts', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

    def test_award_id_change_is_not_allowed(self):
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "cancelled"}})
        old_award_id = self.award_id

        # upload new award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'suppliers': [test_organization]}})
        award = response.json['data']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, award['id'], self.tender_token), {"data": {'qualified': True, "status": "active"}})
        response = self.app.get('/tenders/{}/contracts'.format(
                self.tender_id))
        contract = response.json['data'][-1]
        self.assertEqual(contract['awardID'], award['id'])
        self.assertNotEqual(contract['awardID'], old_award_id)

        # try to update awardID value
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, contract['id'], self.tender_token), {"data": {"awardID": old_award_id}})
        response = self.app.get('/tenders/{}/contracts'.format(
                self.tender_id))
        contract = response.json['data'][-1]
        self.assertEqual(contract['awardID'], award['id'])
        self.assertNotEqual(contract['awardID'], old_award_id)


class TenderNegotiationContractResourceTest(TenderContractResourceTest):
    initial_data = test_tender_negotiation_data
    stand_still_period_days = 10

    def test_patch_tender_contract(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract_id = response.json['data'][0]['id']

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"status": "active"}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn("Can't sign contract before stand-still period end (", response.json['errors'][0]["description"])

        response = self.app.get('/tenders/{}/awards'.format(self.tender_id))
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(len(response.json['data']), 1)
        award = response.json['data'][0]
        start = parse_date(award['complaintPeriod']['startDate'])
        end = parse_date(award['complaintPeriod']['endDate'])
        delta = end - start
        self.assertEqual(delta.days, 0 if SANDBOX_MODE else self.stand_still_period_days)

        # at next steps we test to patch contract in 'complete' tender status
        tender = self.db.get(self.tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"value": {"currency": "USD"}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Can\'t update currency for contract value")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"value": {"valueAddedTaxIncluded": False}}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can\'t update valueAddedTaxIncluded for contract value")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"value": {"amount": 501}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Value amount should be less or equal to awarded amount (469.0)")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"value": {"amount": 238}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['value']['amount'], 238)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")
        self.assertIn(u"dateSigned", response.json['data'])

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "cancelled"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (complete) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "pending"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (complete) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (complete) tender status")

        # at next steps we test to patch contract in 'cancelled' tender status
        response = self.app.post_json('/tenders?acc_token={}', {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender_id = response.json['data']['id']
        tender_token = response.json['access']['token']

        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, tender_token),
                                      {'data': {'suppliers': [test_organization], 'status': 'pending'}})
        award_id = response.json['data']['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, tender_token),
                                       {"data": {'qualified': True, "status": "active"}})

        response = self.app.get('/tenders/{}/contracts'.format(tender_id))
        contract_id = response.json['data'][0]['id']

        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, tender_token),
                                      {'data': {'reason': 'cancellation reason', 'status': 'active'}})
        self.assertEqual(response.status, '201 Created')

        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'cancelled')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            tender_id, contract_id, tender_token),
            {"data": {"awardID": "894917dc8b1244b6aab9ab0ad8c8f48a"}},
            status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            tender_id, contract_id, tender_token), {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update contract in current (cancelled) tender status")

        response = self.app.patch_json('/tenders/{}/contracts/some_id?acc_token={}'.format(
            self.tender_id, self.tender_token), {"data": {"status": "active"}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.patch_json('/tenders/some_id/contracts/some_id', {"data": {"status": "active"}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.get('/tenders/{}/contracts/{}'.format(self.tender_id, self.contract_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")

    def test_tender_contract_signature_date(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.assertNotIn("dateSigned", response.json['data'][0])
        self.contract_id = response.json['data'][0]['id']

        tender = self.db.get(self.tender_id)
        for i in tender.get('awards', []):
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        one_hour_in_furure = (get_now() + timedelta(hours=1)).isoformat()
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"dateSigned": one_hour_in_furure}},
            status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'],
                         [{u'description': [u"Contract signature date can't be in the future"],
                           u'location': u'body',
                           u'name': u'dateSigned'}])

        before_stand_still = i['complaintPeriod']['startDate']
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            {"data": {"dateSigned": before_stand_still}},
            status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.json['errors'], [{u'description': [u'Contract signature date should be after award complaint period end date ({})'.format(i['complaintPeriod']['endDate'])], u'location': u'body', u'name': u'dateSigned'}])

        custom_signature_date = get_now().isoformat()
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"dateSigned": custom_signature_date}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "active")
        self.assertEqual(response.json['data']["dateSigned"], custom_signature_date)
        self.assertIn("dateSigned", response.json['data'])

    def test_items(self):
        response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token))
        tender = response.json['data']

        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract1_id = response.json['data'][0]['id']
        self.assertEqual([item['id'] for item in response.json['data'][0]['items']],
                         [item['id'] for item in tender['items']])


class TenderNegotiationLotContractResourceTest(TenderNegotiationContractResourceTest):
    initial_data = test_tender_negotiation_data
    stand_still_period_days = 10

    def create_award(self):
        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': self.initial_data['items']}})

        # create lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': test_lots[0]})

        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        lot1 = response.json['data']
        self.lot1 = lot1

        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': [{'relatedLot': lot1['id']}]
                                      }
                             })
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending',
                                                          'qualified': True, 'value': {"amount": 469,
                                                                                       "currency": "UAH",
                                                                                       "valueAddedTaxIncluded": True},
                                                          'lotID': lot1['id']}})
        award = response.json['data']
        self.award_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "active"}})

    def test_items(self):
        response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token))
        tender = response.json['data']

        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract1_id = response.json['data'][0]['id']
        self.assertEqual([item['id'] for item in response.json['data'][0]['items']],
                         [item['id'] for item in tender['items'] if item['relatedLot'] == self.lot1['id']])

    def test_award_id_change_is_not_allowed(self):
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "cancelled"}})
        old_award_id = self.award_id

        # upload new award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'suppliers': [test_organization],
                                                'lotID': self.lot1['id']}})
        award = response.json['data']
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, award['id'], self.tender_token), {"data": {'qualified': True, "status": "active"}})
        response = self.app.get('/tenders/{}/contracts'.format(
                self.tender_id))
        contract = response.json['data'][-1]
        self.assertEqual(contract['awardID'], award['id'])
        self.assertNotEqual(contract['awardID'], old_award_id)

        # try to update awardID value
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, contract['id'], self.tender_token), {"data": {"awardID": old_award_id}})
        response = self.app.get('/tenders/{}/contracts'.format(
                self.tender_id))
        contract = response.json['data'][-1]
        self.assertEqual(contract['awardID'], award['id'])
        self.assertNotEqual(contract['awardID'], old_award_id)


class TenderNegotiationLot2ContractResourceTest(BaseTenderContentWebTest):
    initial_data = test_tender_negotiation_data
    stand_still_period_days = 10

    def setUp(self):
        super(TenderNegotiationLot2ContractResourceTest, self).setUp()
        self.create_award()

    def create_award(self):
        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': self.initial_data['items'] * 2}})

        # create lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': test_lots[0]})

        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        lot1 = response.json['data']
        self.lot1 = lot1

        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': test_lots[0]})

        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        lot2 = response.json['data']
        self.lot2 = lot2

        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': [{'relatedLot': lot1['id']},
                                                {'relatedLot': lot2['id']}]
                                      }
                             })
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending',
                                                          'qualified': True, 'value': {"amount": 469,
                                                                                       "currency": "UAH",
                                                                                       "valueAddedTaxIncluded": True},
                                                          'lotID': lot1['id']}})
        award = response.json['data']
        self.award1_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award1_id, self.tender_token), {"data": {"status": "active"}})

        # Create another award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending',
                                                          'qualified': True, 'value': {"amount": 469,
                                                                                       "currency": "UAH",
                                                                                       "valueAddedTaxIncluded": True},
                                                          'lotID': lot2['id']}})
        award = response.json['data']
        self.award2_id = award['id']
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award2_id, self.tender_token), {"data": {"status": "active"}})

    def test_sign_second_contract(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract1_id = response.json['data'][0]['id']
        self.contract2_id = response.json['data'][1]['id']

        # at next steps we test to create contract in 'complete' tender status
        # time travel
        tender = self.db.get(self.tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract2_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'active')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract1_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_create_two_contract(self):
        response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token))
        tender = response.json['data']

        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract1_id = response.json['data'][0]['id']
        self.contract2_id = response.json['data'][1]['id']
        self.assertEqual([item['id'] for item in response.json['data'][0]['items']],
                         [item['id'] for item in tender['items'] if item['relatedLot'] == self.lot1['id']])
        self.assertEqual([item['id'] for item in response.json['data'][1]['items']],
                         [item['id'] for item in tender['items'] if item['relatedLot'] == self.lot2['id']])

        response = self.app.post_json('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award1_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')

        # at next steps we test to create contract in 'complete' tender status
        # time travel
        tender = self.db.get(self.tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract1_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertNotEqual(response.json['data']['status'], 'complete')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract2_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'complete')

        response = self.app.post_json('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award1_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')

        # at next steps we test to create contract in 'cancelled' tender status
        response = self.app.post_json('/tenders?acc_token={}',
                                      {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender_id = response.json['data']['id']
        tender_token = response.json['access']['token']

        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(
            tender_id, tender_token), {'data': {'reason': 'cancellation reason', 'status': 'active'}})
        self.assertEqual(response.status, '201 Created')

        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'cancelled')

        response = self.app.post_json('/tenders/{}/contracts?acc_token={}'.format(tender_id, tender_token),
                                      {'data': {'title': 'contract title',
                                                'description': 'contract description',
                                                'awardID': self.award1_id}},
                                      status=403)
        self.assertEqual(response.status, '403 Forbidden')


class TenderNegotiationQuickContractResourceTest(TenderNegotiationContractResourceTest):
    initial_data = test_tender_negotiation_quick_data
    stand_still_period_days = 5


class TenderNegotiationQuickLotContractResourceTest(TenderNegotiationLotContractResourceTest):
    initial_data = test_tender_negotiation_quick_data
    stand_still_period_days = 5


class TenderNegotiationQuickAccelerationTest(BaseTenderContentWebTest):
    initial_data = test_tender_negotiation_quick_data
    stand_still_period_days = 5
    accelerator = 'quick,accelerator=172800'  # 5 days=432000 sec; 432000/172800=2.5 sec
    time_sleep_in_sec = 3  # time which reduced

    def create_award(self):
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending'}})
        award = response.json['data']
        self.award_id = award['id']
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {'qualified': True, "status": "active"}})

    def setUp(self):
        super(TenderNegotiationQuickAccelerationTest, self).setUp()
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'procurementMethodDetails': self.accelerator}})
        self.assertEqual(response.status, '200 OK')
        self.create_award()

    @unittest.skipUnless(SANDBOX_MODE, "not supported accelerator")
    def test_create_tender_contract_negotination_quick(self):
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract_id = response.json['data'][0]['id']

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertIn("Can't sign contract before stand-still period end (", response.json['errors'][0]["description"])

        time.sleep(self.time_sleep_in_sec)
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')


class TenderNegotiationQuickLotAccelerationTest(TenderNegotiationQuickAccelerationTest):
    initial_data = test_tender_negotiation_quick_data
    stand_still_period_days = 5
    accelerator = 'quick,accelerator=172800'  # 5 days=432000 sec; 432000/172800=2.5 sec
    time_sleep_in_sec = 3  # time which reduced

    def create_award(self):
        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': self.initial_data['items'] * 2}})

        # create lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': test_lots[0]})

        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        lot1 = response.json['data']
        self.lot1 = lot1

        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': [{'relatedLot': lot1['id']}]
                                      }
                             })
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending',
                                                          'qualified': True, 'value': {"amount": 469,
                                                                                       "currency": "UAH",
                                                                                       "valueAddedTaxIncluded": True},
                                                          'lotID': lot1['id']}})
        award = response.json['data']
        self.award_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "active"}})


class TenderNegotiationAccelerationTest(TenderNegotiationQuickAccelerationTest):
    stand_still_period_days = 10
    time_sleep_in_sec = 6


class TenderContractDocumentResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_bids = None

    def create_award(self):
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': {'suppliers': [test_organization], 'status': 'pending'}})
        award = response.json['data']
        self.award_id = award['id']
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "active", 'qualified': True}})

    def setUp(self):
        super(TenderContractDocumentResourceTest, self).setUp()
        self.create_award()
        response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
        self.contract_id = response.json['data'][0]['id']

    def test_not_found(self):
        response = self.app.post('/tenders/some_id/contracts/some_id/documents?acc_token={}',
                                 status=404,
                                 upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.post('/tenders/{}/contracts/some_id/documents?acc_token={}'.format(
            self.tender_id, self.tender_token), status=404, upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            status=404,
            upload_files=[('invalid_value', 'name.doc', 'content')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'body', u'name': u'file'}
        ])

        response = self.app.get('/tenders/some_id/contracts/some_id/documents', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.get('/tenders/{}/contracts/some_id/documents'.format(self.tender_id), status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.get('/tenders/some_id/contracts/some_id/documents/some_id', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.get('/tenders/{}/contracts/some_id/documents/some_id'.format(self.tender_id), status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.get('/tenders/{}/contracts/{}/documents/some_id'.format(self.tender_id, self.contract_id),
                                status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'document_id'}
        ])

        response = self.app.put('/tenders/some_id/contracts/some_id/documents/some_id', status=404,
                                upload_files=[('file', 'name.doc', 'content2')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.put('/tenders/{}/contracts/some_id/documents/some_id?acc_token={}'.format(
            self.tender_id, self.tender_token), status=404, upload_files=[('file', 'name.doc', 'content2')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'contract_id'}
        ])

        response = self.app.put('/tenders/{}/contracts/{}/documents/some_id?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            status=404,
            upload_files=[('file', 'name.doc', 'content2')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'document_id'}
        ])

    def test_create_tender_contract_document(self):
        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        doc_id = response.json["data"]['id']
        self.assertIn(doc_id, response.headers['Location'])
        self.assertEqual('name.doc', response.json["data"]["title"])
        key = response.json["data"]["url"].split('?')[-1]

        response = self.app.get('/tenders/{}/contracts/{}/documents'.format(self.tender_id, self.contract_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"][0]["id"])
        self.assertEqual('name.doc', response.json["data"][0]["title"])

        response = self.app.get('/tenders/{}/contracts/{}/documents?all=true'.format(self.tender_id, self.contract_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"][0]["id"])
        self.assertEqual('name.doc', response.json["data"][0]["title"])

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}?download=some_id'.format(
            self.tender_id, self.contract_id, doc_id), status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'download'}
        ])

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}?{}'.format(
            self.tender_id, self.contract_id, doc_id, key))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/msword')
        self.assertEqual(response.content_length, 7)
        self.assertEqual(response.body, 'content')

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}'.format(
            self.tender_id, self.contract_id, doc_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"]["id"])
        self.assertEqual('name.doc', response.json["data"]["title"])

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "cancelled"}})
        self.assertEqual(response.json['data']["status"], "cancelled")

        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            upload_files=[('file', 'name.doc', 'content')],
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't add document in current contract status")

        self.set_status('complete')

        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token),
            upload_files=[('file', 'name.doc', 'content')],
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't add document in current (complete) tender status")

    def test_put_tender_contract_document(self):
        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        doc_id = response.json["data"]['id']
        self.assertIn(doc_id, response.headers['Location'])

        response = self.app.put('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            status=404,
            upload_files=[('invalid_name', 'name.doc', 'content')])
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'body', u'name': u'file'}
        ])

        response = self.app.put('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            upload_files=[('file', 'name.doc', 'content2')])
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"]["id"])
        key = response.json["data"]["url"].split('?')[-1]

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}?{}'.format(
            self.tender_id, self.contract_id, doc_id, key))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/msword')
        self.assertEqual(response.content_length, 8)
        self.assertEqual(response.body, 'content2')

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}'.format(
            self.tender_id, self.contract_id, doc_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"]["id"])
        self.assertEqual('name.doc', response.json["data"]["title"])

        response = self.app.put('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token), 'content3', content_type='application/msword')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"]["id"])
        key = response.json["data"]["url"].split('?')[-1]

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}?{}'.format(
            self.tender_id, self.contract_id, doc_id, key))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/msword')
        self.assertEqual(response.content_length, 8)
        self.assertEqual(response.body, 'content3')

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), {"data": {"status": "cancelled"}})
        self.assertEqual(response.json['data']["status"], "cancelled")

        response = self.app.put('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            upload_files=[('file', 'name.doc', 'content3')],
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update document in current contract status")

        self.set_status('complete')

        response = self.app.put('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            upload_files=[('file', 'name.doc', 'content3')],
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update document in current (complete) tender status")

    def test_patch_tender_contract_document(self):
        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            self.tender_id, self.contract_id, self.tender_token), upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        doc_id = response.json["data"]['id']
        self.assertIn(doc_id, response.headers['Location'])

        response = self.app.patch_json('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            {"data": {"description": "document description"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"]["id"])

        response = self.app.get('/tenders/{}/contracts/{}/documents/{}'.format(
            self.tender_id, self.contract_id, doc_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(doc_id, response.json["data"]["id"])
        self.assertEqual('document description', response.json["data"]["description"])

        # cancel contract by award cancellation
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "cancelled"}})
        self.assertEqual(response.json['data']["status"], "cancelled")

        response = self.app.patch_json('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            {"data": {"description": "document description"}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update document in current contract status")

        self.set_status('complete')

        response = self.app.patch_json('/tenders/{}/contracts/{}/documents/{}?acc_token={}'.format(
            self.tender_id, self.contract_id, doc_id, self.tender_token),
            {"data": {"description": "document description"}},
            status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"],
                         "Can't update document in current (complete) tender status")


class TenderContractNegotiationDocumentResourceTest(TenderContractDocumentResourceTest):
    initial_data = test_tender_negotiation_data


class TenderContractNegotiationLotDocumentResourceTest(TenderContractDocumentResourceTest):
    initial_data = test_tender_negotiation_data

    def create_award(self):
        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': self.initial_data['items'] * 2}})

        # create lot
        response = self.app.post_json('/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                                      {'data': test_lots[0]})

        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        lot1 = response.json['data']
        self.lot1 = lot1

        self.app.patch_json('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
                            {'data': {'items': [{'relatedLot': lot1['id']}]
                                      }
                             })
        # Create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            self.tender_id, self.tender_token), {'data': {'suppliers': [test_organization], 'status': 'pending',
                                                          'qualified': True, 'value': {"amount": 469,
                                                                                       "currency": "UAH",
                                                                                       "valueAddedTaxIncluded": True},
                                                          'lotID': lot1['id']}})
        award = response.json['data']
        self.award_id = award['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
            self.tender_id, self.award_id, self.tender_token), {"data": {"status": "active"}})


class TenderContractNegotiationQuickDocumentResourceTest(TenderContractNegotiationDocumentResourceTest):
    initial_data = test_tender_negotiation_quick_data


class TenderContractNegotiationQuickLotDocumentResourceTest(TenderContractNegotiationLotDocumentResourceTest):
    initial_data = test_tender_negotiation_quick_data


def prepare_bids(init_bids):
    """Make different identifier id for every bid"""
    init_bids = deepcopy(init_bids)
    base_identifier_id = int(init_bids[0]['tenderers'][0]['identifier']['id'])

    for bid in init_bids:
        base_identifier_id += 1
        bid['tenderers'][0]['identifier']['id'] = '{:0=8}'.format(base_identifier_id)

        return init_bids


class TenderMergedContracts2LotsResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_bids = prepare_bids(test_bids)
    initial_auth = ('Basic', ('broker', ''))

    RESPONSE_CODE = {
        '200': '200 OK',
        '201': '201 Created',
        '403': '403 Forbidden',
        '404': '404 Not Found',
        '415': '415 Unsupported Media Type',
        '422': '422 Unprocessable Entity'
    }

    def create_awards(self):
        """Create two awards and return them"""
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))

        # Create two awards
        awards_response = list()

        for i in range(len(self.initial_lots)):
            awards_response.append(self.app.post_json(
                '/tenders/{}/awards'.format(self.tender_id), {
                    'data':
                        {
                            'suppliers': self.initial_bids[0]['tenderers'],
                            'status': 'pending',
                            'bid_id': self.initial_bids[0]['id'],
                            'value': self.initial_bids[0]['lotValues'][i]['value'],
                            'lotID': self.initial_bids[0]['lotValues'][i]['relatedLot']
                        }
                }
            ).json['data'])

        self.app.authorization = authorization

        return awards_response

    def active_awards(self, *args):
        for award_id in args:
            self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
                self.tender_id, award_id, self.tender_token),
                {'data': {'status': 'active'}}
            )

    def test_not_found_contract_for_award(self):
        """Try merge contracts which doesn't exist"""
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id)

        # Get second and change status to active but don't create contract
        tender = self.db.get(self.tender_id)
        second_award = tender['awards'][1]
        second_award['status'] = 'active'

        self.db.save(tender)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        contracts = response.json['data']

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, contracts[0]['id'], self.tender_token),
            {'data': {'additionalAwardIDs': [second_award_id]}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertEqual(response.json['errors'], [
            {'location': 'body', 'name': 'additionalAwardIDs',
             'description': 'Can\'t found contract for award {award_id}".format(award_id=second_award_id)'}
        ])

    def test_try_merge_not_real_award(self):
        """Can't merge award which doesn't exist"""
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        # Try send not real award id
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'additionalAwardIDs': [uuid4().hex]}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertEqual(response.json['errors'], [
            {'location': 'body', 'name': 'additionalAwardIDs', 'description': ['id must be one of award id']}
        ])

    def test_try_merge_itself(self):
        """Can't merge contract if self contract"""
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get(
            '/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token)
        )
        first_contract, second_contract = response.json['data']

        # Try send itself
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, first_contract['id'], self.tender_token,
            {'data': {'additionalAwardIDs': [first_contract['awardID']]}}, status=422
        ))

        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertEqual(response.json['errors'], [
            {'location': 'body', 'name': 'additionalAwardIDs', 'description': ['Can\'t merge itself']}
        ])

    def test_standstill_period(self):
        """
        Create two awards and merged them and try set status active for main
        contract while additional award has stand still period
        """
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID']]

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, first_contract['id'], self.tender_token,
            {'data': {'additionalAwardIDs': additionalAwardIDs}}
        ))
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']
        self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
        self.assertEqual(first_contract['id'], second_contract['mergedInto'])
        self.assertEqual(second_contract['status'], 'merged')

        # Update complaintPeriod for additional award
        tender = self.db.get(self.tender_id)
        now = get_now()
        tender['awards'][0]['complaitPeriod'] = {
            'startDate': (now - timedelta(days=1)).isoformat(),
            'endDate': (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            'startDate': (now - timedelta(days=1)).isoformat(),
            'endDate': (now - timedelta(days=1)).isoformat()
        }
        self.db.save()

        dateSigned = get_now().isoformat()

        # Try set status active for main contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'status': 'active'}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertIn(
            'Can\'t sign contract before stand-still additional awards period end',
            response.json['errors'][0]['description']
        )

        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            'startDate': (now - timedelta(days=1)).isoformat(),
            'endDate': (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            'startDate': (now - timedelta(days=1)).isoformat(),
            'endDate': (now - timedelta(days=1)).isoformat()
        }

        self.db.save(tender)

        # Try set status active for main contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'dateSigned': dateSigned, 'status': 'active'}}
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['status'], 'active')
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

    def test_activate_contract_with_complaint(self):
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID']]

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, first_contract['id'], self.tender_token,
            {'data': {'additionalAwardIDs': additionalAwardIDs}}
        ))
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']
        self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
        self.assertEqual(first_contract['id'], second_contract['mergedInto'])
        self.assertEqual(second_contract['status'], 'merged')

        # Create complaint on additional award
        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints'.format(self.tender_id, second_contract['awardID']),
            {'data': {
                'title': 'complaint title',
                'description': 'complaint description',
                'author': test_organization,
                'status': 'claim'
            }}
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        complaint = response.json['data']
        owner_token = response.json['access']['token']

        # Update complaintPeriod for additional award
        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try set status active for main contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'dateSigned': get_now().isoformat(), 'status': 'active'}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                'location': 'body',
                'name': 'data',
                'description': 'Can\'t sign contract before reviewing all additional complaints'
            }
        ])

        # Lets resolve complaint
        self.edit_award_complaint(
            second_contract['awardID'], complaint['id'], self.tender_token,
            {'data': {'status': 'answered', 'resolutionType': 'resolved', 'resolution': 'resolution text ' * 2}}
        )
        self.edit_award_complaint(
            second_contract['awardID'], complaint['id'], owner_token,
            {'data': {'status': 'resolved', 'satisfied': True}}
        )

        # Try sign contract again
        dateSigned = get_now().isoformat()
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'dateSigned': dateSigned, 'status': 'active'}}
        )
        self.assertEqual(response.json['data']['status'], 'active')
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

    def test_cancel_award(self):
        """Create two awards and merged them and then cancel additional award"""
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID']]

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, first_contract['id'], self.tender_token,
            {'data': {'additionalAwardIDs': additionalAwardIDs}}
        ))
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']
        self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
        self.assertEqual(first_contract['id'], second_contract['mergedInto'])
        self.assertEqual(second_contract['status'], 'merged')

        # Cancel additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, second_award_id, self.tender_token),
            {'data': {'status': 'canceled'}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(
            response.json['errors'][0]['description'],
            'Can\'t cancel award while it is a part of merged contracts.'
        )

    def test_cancel_main_award(self):
        """Create two awards and merged them and then cancel main award"""
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID']]

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, first_contract['id'], self.tender_token,
            {'data': {'additionalAwardIDs': additionalAwardIDs}}
        ))
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']
        self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
        self.assertEqual(first_contract['id'], second_contract['mergedInto'])
        self.assertEqual(second_contract['status'], 'merged')

        # Cancel additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_award_id, self.tender_token),
            {'data': {'status': 'cancelled'}}
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Check cancel award
        response = self.app.get(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token)
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['status'], 'cancelled')

        # Check contracts
        response = self.app('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 2)
        self.assertNotIn('additionalAwardIDs', response.json['data'][0])
        self.assertEqual(response.json['data'][1]['status'], 'pending')

        # Check that new award was created and has status pending
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 2)
        self.assertEqual(response.json['data'][-1]['status'], 'pending')

    def test_merge_two_contracts_with_different_supliers_ids(self):
        """Try merge contracts with different suppliers"""
        self.app.authorization = ('Basic', ('token', ''))

        # Create two awards
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': test_lots[0]}
        )

        first_award_response = self.app.post_json(
            '/tenders/{}/awards'.format(self.tender_id),
            {'data': {
                'suppliers': [test_organization],
                'status': 'pending',
                'value': response.json['data']['value'],
                'lotID': response.json['data']['id']
            }}
        )

        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': test_lots[0]}
        )

        second_award_response = self.app.post_json(
            '/tenders/{}/awards'.format(self.tender_id),
            {'data': {
                'suppliers': [test_organization],
                'status': 'pending',
                'value': response.json['data']['value'],
                'lotID': response.json['data']['id']
            }}
        )
        first_award = first_award_response.json['data']
        first_award_id = first_award['id']
        second_award = second_award_response.json['data']
        second_award_id = second_award['id']
        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        # Try merge first contract to second
        additionalAwardIDs = [second_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'additionalAwardIDs': additionalAwardIDs}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertEqual(response.json['errors'], [
            {'location': 'body', 'name': 'additionalAwardIDs', 'description': ['Awards must have same suppliers id']}
        ])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        self.assertNotIn('additionalAwardIDs', first_contract)
        self.assertNotIn('mergedInto', second_contract)
        self.assertNotEqual(second_contract['status'], 'merged')

    def test_merge_two_contracts_with_different_suppliers_scheme(self):
        self.app.authorization = ('Basic', ('token', ''))

        # Set different scheme
        # Create two awards
        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': test_lots[0]}
        )

        test_organization['identifier']['scheme'] = 'UA-EDR'

        first_award_response = self.app.post_json(
            '/tenders/{}/awards'.format(self.tender_id),
            {'data': {
                'suppliers': [test_organization],
                'status': 'pending',
                'value': response.json['data']['value'],
                'lotID': response.json['data']['id']
            }}
        )

        response = self.app.post_json(
            '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': test_lots[0]}
        )

        test_organization['identifier']['scheme'] = 'LV-RE'

        second_award_response = self.app.post_json(
            '/tenders/{}/awards'.format(self.tender_id),
            {'data': {
                'suppliers': [test_organization],
                'status': 'pending',
                'value': response.json['data']['value'],
                'lotID': response.json['data']['id']
            }}
        )
        first_award = first_award_response.json['data']
        first_award_id = first_award['id']
        second_award = second_award_response.json['data']
        second_award_id = second_award['id']
        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        # Try merge first contract to second
        additionalAwardIDs = [second_contract['awardID']]
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'additionalAwardIDs': additionalAwardIDs}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertEqual(response.json['errors'], [
            {
                'location': 'body',
                'name': 'additionalAwardIDs',
                'description': ['Awards must have same suppliers schema']
            }
        ])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        self.assertNotIn('additionalAwardIDs', first_contract)
        self.assertNotIn('mergedInto', second_contract)
        self.assertNotEqual(second_contract['status'], 'merged')

    def test_set_big_value(self):
        """Create two awards and merged them"""
        first_award, second_award = self.create_awards()
        first_award_id = first_award['id']
        second_award_id = second_award['id']

        self.active_awards(first_award_id, second_award_id)

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID']]

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            self.tender_id, first_contract['id'], self.tender_token,
            {'data': {'additionalAwardIDs': additionalAwardIDs}}
        ))
        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']
        self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
        self.assertEqual(first_contract['id'], second_contract['mergedInto'])
        self.assertEqual(second_contract['status'], 'merged')

        max_value = first_contract['value']['amount'] + second_award['value']['amount']

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'value': {'amount': max_value + 0.1}}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(
            response.json['errors'][0]['description'],
            'Value amount should be less or equal to awarded amount ({value:.1f})'.format(value=max_value)
        )


class TenderMergedContracts3LotsResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_bids = prepare_bids(test_bids)
    initial_auth = ('Basic', ('broker', ''))

    RESPONSE_CODE = {
        '200': '200 OK',
        '201': '201 Created',
        '403': '403 Forbidden',
        '404': '404 Not Found',
        '415': '415 Unsupported Media Type',
        '422': '422 Unprocessable Entity'
    }

    def create_awards(self):
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))

        # Create three awards
        awards_response = list()

        for i in range(len(self.initial_lots)):
            awards_response.append(self.app.post_json(
                '/tenders/{}/awards'.format(self.tender_id), {
                    'data':
                        {
                            'suppliers': self.initial_bids[0]['tenderers'],
                            'status': 'pending',
                            'bid_id': self.initial_bids[0]['id'],
                            'value': self.initial_bids[0]['lotValues'][i]['value'],
                            'lotID': self.initial_bids[0]['lotValues'][i]['relatedLot']
                        }
                }
            ).json['data'])

        self.app.authorization = authorization

        return awards_response

    def active_awards(self, awards):
        for award in awards:
            self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(
                    self.tender_id, award.json['data']['id'], self.tender_token
                ), {"data": {"status": "active"}}
            )

    def test_merge_three_contracts(self):
        """Create two awards and merged them"""

        awards = self.create_awards()
        self.active_awards(awards)

        # Get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID'], third_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")

        # Set stand still period
        tender = self.db.get(self.tender_id)
        now = get_now()
        for award in tender['awards']:
            award['complaintPeriod'] = {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            }
        self.db.save(tender)

        # Set status active for first contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'status': 'active'}}
        )

        self.assertEqual(response.json['data']['status'], 'active')

        # Check tender status
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_standstill_period(self):
        """
        Create two awards and merged them and try set status active for main
        contract while additional award has stand still period
        """

        # Create and active awards
        awards = self.create_awards()
        self.active_awards(awards)

        # Get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID'], third_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")

        # Update complaintPeriod for additional award
        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now + timedelta(days=1)).isoformat(),
            "endDate": (now + timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        dateSigned = get_now().isoformat()

        # Try set status active for main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertIn(
            "Can't sign contract before stand-still additional awards period end",
            response.json['errors'][0]['description']
        )

        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try set status active for main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned, "status": "active"}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['status'], 'active')
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

    def test_activate_contract_with_complaint(self):

        awards = self.create_awards()
        self.active_awards(awards)

        # Get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID'], third_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")

        # Create complaint on first additional award
        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints'.format(self.tender_id, second_contract['awardID']),
            {'data': {
                'title': 'complaint title',
                'description': 'complaint description',
                'author': test_organization,
                'status': 'claim'
            }}
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['201'])
        second_award_complaint = response.json['data']
        second_award_complaint_owner_token = response.json['access']['token']

        # Create complaint on second additional award
        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints'.format(self.tender_id, third_contract['awardID']),
            {'data': {
                'title': 'complaint title',
                'description': 'complaint description',
                'author': test_organization,
                'status': 'claim'
            }}
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['201'])
        third_award_complaint = response.json['data']
        third_award_complaint_owner_token = response.json['access']['token']

        # Update complaintPeriod for awards
        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try set status active for main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "data",
                "description": "Can't sign contract before reviewing all additional complaints"
            }
        ])

        # Lets resolve first complaint
        self.edit_award_complaint(
            second_contract['awardID'],
            second_award_complaint['id'],
            self.tender_token,
            {
                "data": {"status": "answered",
                         "resolutionType": "resolved",
                         "resolution": "resolution text " * 2}
            })

        self.edit_award_complaint(
            second_contract['awardID'],
            second_award_complaint['id'],
            second_award_complaint_owner_token,
            {"data": {"satisfied": True, "status": "resolved"}}
        )

        # Try set status active for main contract again
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "data",
                "description": "Can't sign contract before reviewing all additional complaints"
            }
        ])

        # Lets resolve second complaint
        self.edit_award_complaint(
            third_contract['awardID'],
            third_award_complaint['id'],
            self.tender_token,
            {"data": {"status": "answered", "resolutionType": "resolved", "resolution": "resolution text " * 2}}
        )

        self.edit_award_complaint(
            third_contract['awardID'],
            third_award_complaint['id'],
            third_award_complaint_owner_token,
            {"data": {"satisfied": True, "status": "resolved"}}
        )

        # And try sign contract again
        dateSigned = get_now().isoformat()
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned, "status": "active"}}
        )

        self.assertEqual(response.json['data']['status'], 'active')
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

    def test_cancel_award(self):
        """Create two awards and merged them and try to cancel both"""
        awards = self.create_awards()
        self.active_awards(awards)

        # get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID'], third_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")

        # Cancel additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, second_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(
            response.json['errors'][0]['description'], "Can't cancel award while it is a part of merged contracts."
        )

        # Check main contract
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 2)

        # Cancel second additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, third_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertIn(
            "Can\'t cancel award while it is a part of merged contracts.", response.json['errors'][0]['description']
        )

        # Check main contract
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 2)

    def test_cancel_main_award(self):
        """Create two awards and merged them and then cancel main contract"""
        awards = self.create_awards()
        self.active_awards(awards)

        # Get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID'], third_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")

        # Cancel additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Check cancelled award
        response = self.app.get(
            '/tenders/{}/contracts/{}?acc_token'.format(self.tender_id, first_contract['id'], self.tender_token)
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['status'], 'cancelled')
        self.assertNotIn('additionalAwardIDs', response.json['data']['status'])

        # Check rest contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(response.json['data'][1]['status'], 'pending')
        self.assertEqual(response.json['data'][2]['status'], 'pending')

        # Check that new awards were created and has status pending
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 4)
        self.assertEqual(response.json['data'][-1]['status'], 'pending')

    def test_try_merge_pending_award(self):
        awards = self.create_awards()
        self.active_awards(awards[:-1])

        # Get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract = response.json['data']

        # For third award didn't create contract
        additionalAwardIDs = [second_contract['awardID'], awards[-1].json['data']['id']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}, status=422
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "additionalAwardIDs",
                "description": ["awards must has status active"]
            }
        ])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract = response.json['data']
        self.assertNotIn('additionalAwardIDs', first_contract)
        self.assertNotIn('mergedInto', second_contract)
        self.assertNotEqual(second_contract["status"], "merged")

    def test_additional_awards_dateSigned(self):
        """Try set dateSigned before end complaint period for additional awards"""

        awards = self.create_awards()
        self.active_awards(awards)

        # get created contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract = response.json['data']

        additionalAwardIDs = [second_contract['awardID'], third_contract['awardID']]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")

        # Update complaintPeriod for additional award
        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now + timedelta(days=1)).isoformat(),
            "endDate": (now + timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        dateSigned = get_now().isoformat()

        # Try set status active for main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertIn(
            "Contract signature date should be after additional awards complaint period end date",
            response.json['errors'][0]['description'][0]
        )

        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try set status active for main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)


class TenderMergedContracts4LotsResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_bids = prepare_bids(test_bids)
    initial_auth = ('Basic', ('broker', ''))

    RESPONSE_CODE = {
        '200': '200 OK',
        '201': '201 Created',
        '403': '403 Forbidden',
        '404': '404 Not Found',
        '415': '415 Unsupported Media Type',
        '422': '422 Unprocessable Entity'
    }

    def create_awards(self):
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))

        # Create four awards
        awards_response = list()

        for i in range(len(self.initial_lots)):
            awards_response.append(self.app.post_json(
                '/tenders/{}/awards'.format(self.tender_id), {
                    'data':
                        {
                            'suppliers': self.initial_bids[0]['tenderers'],
                            'status': 'pending',
                            'bid_id': self.initial_bids[0]['id'],
                            'value': self.initial_bids[0]['lotValues'][i]['value'],
                            'lotID': self.initial_bids[0]['lotValues'][i]['relatedLot']
                        }
                }
            ).json['data'])

        self.app.authorization = authorization

        return awards_response

    def active_awards(self, awards):
        for award in awards:
            self.app.patch_json(
                '/tenders/{}/awards/{}?acc_token={}'.format(
                    self.tender_id, award.json['data']['id'], self.tender_token
                ), {"data": {"status": "active"}}
            )

    def test_merge_four_contracts(self):
        """Create four awards and merged them"""
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        additionalAwardIDs = [award_response.json['data']['id'] for award_response in awards_response[1:]]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(first_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Remove additionalAwardIDs
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": []}})

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertNotIn('additionalAwardIDs', first_contract)
        self.assertNotIn('mergedInto', second_contract)
        self.assertNotIn('mergedInto', third_contract)
        self.assertNotIn('mergedInto', fourth_contract)
        self.assertNotEqual(second_contract["status"], "merged")
        self.assertNotEqual(third_contract["status"], "merged")
        self.assertNotEqual(fourth_contract["status"], "merged")

    def test_sign_contract(self):
        """Create four awards and merged them and sign main contracts"""
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        additionalAwardIDs = [award_response.json['data']['id'] for award_response in awards_response[1:]]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": additionalAwardIDs}})

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(first_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # set stand still period
        tender = self.db.get(self.tender_id)
        now = get_now()

        for award in tender['awards']:
            award['complaintPeriod'] = {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            }
        self.db.save(tender)

        # Set status active for first contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'status': 'active'}}
        )

        self.assertEqual(response.json['data']['status'], 'active')

        # Check tender status
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_cancel_award(self):
        """Create two awards and merged them and try to cancel both"""

        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        additionalAwardIDs = [award_response.json['data']['id'] for award_response in awards_response[1:]]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(first_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Cancel first additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, second_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(
            response.json['errors'][0]['description'],
            "Can't cancel award while it is a part of merged contracts."
        )

        # Check main contract
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 4)
        self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 3)

        # Cancel second additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, third_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(
            response.json['errors'][0]['description'],
            "Can't cancel award while it is a part of merged contracts."
        )

        # Check main contract
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 4)
        self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 3)

        # Cancel third additional award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, fourth_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(
            response.json['errors'][0]['description'],
            "Can't cancel award while it is a part of merged contracts."
        )

        # Check main contract
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 4)
        self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 3)

    def test_cancel_main_award(self):
        """Create two awards and merged them and then main"""
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        additionalAwardIDs = [award_response.json['data']['id'] for award_response in awards_response[1:]]

        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], third_contract["mergedInto"])
        self.assertEqual(first_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(third_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Cancel main award
        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_contract['awardID'], self.tender_token),
            {'data': {'status': 'cancelled'}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Check main award
        response = self.app.get(
            '/tenders/{}/contracts/{}?acc_token'.format(self.tender_id, first_contract['id'], self.tender_token)
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['status'], 'cancelled')
        self.assertNotIn('additionalAwardIDs', response.json['data'])

        # Check contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 4)
        self.assertEqual('pending', response.json['data'][1]['status'])
        self.assertEqual('pending', response.json['data'][2]['status'])
        self.assertEqual('pending', response.json['data'][3]['status'])
        self.assertNotIn('mergedInto', response.json['data'][1])
        self.assertNotIn('mergedInto', response.json['data'][2])
        self.assertNotIn('mergedInto', response.json['data'][3])

        # Check that new awards were created and have status pending
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(len(response.json['data']), 5)
        self.assertEqual(response.json['data'][-1]['status'], 'pending')

    def test_cancel_first_main_award(self):
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_additionalAwardIDs = [awards_response[1].json['data']['id']]
        second_additionalAwardIDs = [awards_response[3].json['data']['id']]

        # Merge contracts
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": second_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(third_contract["additionalAwardIDs"], second_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(third_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Cancel first main contract

        response = self.app.patch_json(
            '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_contract['awardID'], self.tender_token),
            {"data": {"status": "cancelled"}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        self.assertEqual(response.json['data']['status'], 'cancelled')

        # Check rest contracts
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract['status'], 'cancelled')
        self.assertEqual(second_contract['status'], 'pending')
        self.assertNotIn('additionalAwardIDs', first_contract)
        self.assertNotIn('mergedInto', second_contract)
        self.assertEqual(third_contract['additionalAwardIDs'], second_additionalAwardIDs)
        self.assertEqual(third_contract['status'], 'pending')
        self.assertEqual(fourth_contract['status'], 'merged')
        self.assertEqual(fourth_contract['mergedInto'], third_contract['id'])

    def test_merge_by_two_contracts(self):
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_additionalAwardIDs = [awards_response[1].json['data']['id']]
        second_additionalAwardIDs = [awards_response[3].json['data']['id']]

        # Merge contracts
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": second_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(third_contract["additionalAwardIDs"], second_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(third_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # set stand still period
        tender = self.db.get(self.tender_id)
        now = get_now()
        for award in tender['awards']:
            award['complaintPeriod'] = {
                "startDate": (now - timedelta(days=1)).isoformat(),
                "endDate": (now - timedelta(days=1)).isoformat()
            }

        self.db.save(tender)

        # Set status active for first contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
            {'data': {'status': 'active'}}
        )

        self.assertEqual(response.json['data']['status'], 'active')

        # Check tender status, tender must have status 'active.awarded;
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertNotEqual(response.json['data']['status'], 'complete')

        # Set status active for first contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, third_contract['id'], self.tender_token),
            {'data': {'status': 'active'}}
        )

        # and check tender status
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_try_merge_main_contract(self):
        """Try merge contract which has additionalAwardIDs"""
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_additionalAwardIDs = [awards_response[1].json['data']['id']]

        # Merge contracts
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": [contract_response.json['data'][0]['awardID']]}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertNotEqual(fourth_contract["status"], "merged")

    def test_try_merge_contract_two_times(self):
        """ Check that we can merge contract 2 times in different contracts """
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_additionalAwardIDs = [awards_response[1].json['data']['id']]
        second_additionalAwardIDs = [awards_response[3].json['data']['id']]

        # Merge contracts
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": second_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(third_contract["additionalAwardIDs"], second_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(third_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Try merge contract which already merge
        first_additionalAwardIDs.append(awards_response[3].json['data']['id'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}, status=403
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "data",
                "description": "Can't merge contract in status merged"
            }
        ])

        # Remove fourth contract from second_additionalAwardIDs
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": []}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        # Check fourth contract
        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertNotEqual('mergedInto', fourth_contract)
        self.assertNotEqual(fourth_contract["status"], "merged")

        # Merge fourth contract
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(first_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

    def test_activate_contract_with_complaint(self):
        """" Try activate main contract while additional wards has complaints """
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_additionalAwardIDs = [awards_response[1].json['data']['id']]
        second_additionalAwardIDs = [awards_response[3].json['data']['id']]

        # Merge contracts
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": second_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(third_contract["additionalAwardIDs"], second_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(third_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Create complaint on first additional award
        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints'.format(self.tender_id, second_contract['awardID']),
            {'data': {
                'title': 'complaint title',
                'description': 'complaint description',
                'author': test_organization,
                'status': 'claim'
            }}
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['201'])
        second_award_complaint = response.json['data']
        second_award_complaint_owner_token = response.json['access']['token']

        # Create complaint on second additional award
        response = self.app.post_json(
            '/tenders/{}/awards/{}/complaints'.format(self.tender_id, fourth_contract['awardID']),
            {'data': {
                'title': 'complaint title',
                'description': 'complaint description',
                'author': test_organization,
                'status': 'claim'
            }})
        self.assertEqual(response.status, self.RESPONSE_CODE['201'])
        fourth_award_complaint = response.json['data']
        fourth_award_complaint_owner_token = response.json['access']['token']

        # Update complaintPeriod for awards
        tender = self.db.get(self.tender_id)
        now = get_now()
        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][3]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try set status active for first main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "data",
                "description": "Can't sign contract before reviewing all additional complaints"
            }
        ])

        # Try set status active for second main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "data",
                "description": "Can't sign contract before reviewing all additional complaints"
            }
        ])

        # Lets resolve first complaint
        self.edit_award_complaint(
            second_contract['awardID'], second_award_complaint['id'], self.tender_token,
            {"data": {
                "status": "answered",
                "resolutionType": "resolved",
                "resolution": "resolution text " * 2}
            }
        )

        self.edit_award_complaint(
            second_contract['awardID'], second_award_complaint['id'],
            second_award_complaint_owner_token,
            {"data": {"satisfied": True, "status": "resolved"}}
        )

        # Try sign first main contract again
        dateSigned = get_now().isoformat()
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned, "status": "active"}}
        )

        self.assertEqual(response.json['data']['status'], 'active')
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

        # Try set status active for second main contract again
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, third_contract['id'], self.tender_token),
            {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=403
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['403'])
        self.assertEqual(response.json['errors'], [
            {
                "location": "body",
                "name": "data",
                "description": "Can't sign contract before reviewing all additional complaints"
            }
        ])

        # Lets resolve second complaint
        self.edit_award_complaint(
            fourth_contract['awardID'], fourth_award_complaint['id'], self.tender_token,
            {"data": {
                "status": "answered",
                "resolutionType": "resolved",
                "resolution": "resolution text " * 2
            }}
        )

        self.edit_award_complaint(
            fourth_contract['awardID'], fourth_award_complaint['id'],
            fourth_award_complaint_owner_token,
            {"data": {"satisfied": True, "status": "resolved"}}
        )

        # And try sign contract again
        dateSigned = get_now().isoformat()
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, third_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned, "status": "active"}}
        )

        self.assertEqual(response.json['data']['status'], 'active')
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

    def test_additional_awards_dateSigned(self):
        """ Try set dateSigned before end complaint period for additional awards """
        awards_response = self.create_awards()
        self.active_awards(awards_response)

        # Get created contracts
        contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
        first_additionalAwardIDs = [awards_response[1].json['data']['id']]
        second_additionalAwardIDs = [awards_response[3].json['data']['id']]

        # Merge contracts
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][0]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": first_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        response = self.app.patch_json(
            '/tenders/{}/contracts/{}?acc_token={}'.format(
                self.tender_id, contract_response.json['data'][2]['id'], self.tender_token
            ), {"data": {"additionalAwardIDs": second_additionalAwardIDs}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])

        # Get contracts and check fields
        response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

        first_contract, second_contract, third_contract, fourth_contract = response.json['data']
        self.assertEqual(first_contract["additionalAwardIDs"], first_additionalAwardIDs)
        self.assertEqual(third_contract["additionalAwardIDs"], second_additionalAwardIDs)
        self.assertEqual(first_contract["id"], second_contract["mergedInto"])
        self.assertEqual(third_contract["id"], fourth_contract["mergedInto"])
        self.assertEqual(second_contract["status"], "merged")
        self.assertEqual(fourth_contract["status"], "merged")

        # Update complaintPeriod for additional award
        tender = self.db.get(self.tender_id)
        now = get_now()

        tender['awards'][0]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now + timedelta(days=1)).isoformat(),
            "endDate": (now + timedelta(days=1)).isoformat()
        }
        tender['awards'][2]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        tender['awards'][3]['complaintPeriod'] = {
            "startDate": (now + timedelta(days=1)).isoformat(),
            "endDate": (now + timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        dateSigned = get_now().isoformat()

        # Try set status active for first main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertIn(
            "Contract signature date should be after additional awards complaint period end date",
            response.json['errors'][0]['description'][0]
        )

        tender = self.db.get(self.tender_id)
        now = get_now()
        tender['awards'][1]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try now set status active for first main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)

        # Try set status active for second main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, third_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned}}, status=422
        )
        self.assertEqual(response.status, self.RESPONSE_CODE['422'])
        self.assertIn(
            "Contract signature date should be after additional awards complaint period end date",
            response.json['errors'][0]['description'][0]
        )

        tender = self.db.get(self.tender_id)
        now = get_now()
        tender['awards'][3]['complaintPeriod'] = {
            "startDate": (now - timedelta(days=1)).isoformat(),
            "endDate": (now - timedelta(days=1)).isoformat()
        }
        self.db.save(tender)

        # Try set status active for main contract
        response = self.app.patch_json(
            "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, third_contract['id'], self.tender_token),
            {"data": {"dateSigned": dateSigned}}
        )

        self.assertEqual(response.status, self.RESPONSE_CODE['200'])
        self.assertEqual(response.json['data']['dateSigned'], dateSigned)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderContractResourceTest))
    suite.addTest(unittest.makeSuite(TenderContractDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderMergedContracts2LotsResourceTest))
    suite.addTest(unittest.makeSuite(TenderMergedContracts3LotsResourceTest))
    suite.addTest(unittest.makeSuite(TenderMergedContracts4LotsResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
