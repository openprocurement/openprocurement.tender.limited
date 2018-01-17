# -*- coding: utf-8 -*-
import time
import unittest
from datetime import time, timedelta
from uuid import uuid4

from iso8601 import parse_date
from openprocurement.api.constants import SANDBOX_MODE
from openprocurement.api.utils import get_now
from openprocurement.tender.belowthreshold.tests.base import test_organization
from base import test_lots


# TenderContractResourceTest
def create_tender_contract_invalid(self):
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


def create_tender_contract(self):
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


def patch_tender_contract(self):
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


def tender_contract_signature_date(self):
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


def get_tender_contract(self):
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


def get_tender_contracts(self):
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


def award_id_change_is_not_allowed(self):
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


# TenderNegotiationContractResourceTest
def patch_tender_negotiation_contract(self):
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


def tender_negotiation_contract_signature_date(self):
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
    self.assertEqual(response.json['errors'], [{u'description': [
        u'Contract signature date should be after award complaint period end date ({})'.format(
            i['complaintPeriod']['endDate'])], u'location': u'body', u'name': u'dateSigned'}])

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


def items(self):
    response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token))
    tender = response.json['data']

    response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
    self.contract1_id = response.json['data'][0]['id']
    self.assertEqual([item['id'] for item in response.json['data'][0]['items']],
                     [item['id'] for item in tender['items']])


# TenderNegotiationLotContractResourceTest
def lot_items(self):
    response = self.app.get('/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token))
    tender = response.json['data']

    response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
    self.contract1_id = response.json['data'][0]['id']
    self.assertEqual([item['id'] for item in response.json['data'][0]['items']],
                     [item['id'] for item in tender['items'] if item['relatedLot'] == self.lot1['id']])


def lot_award_id_change_is_not_allowed(self):
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


def activate_contract_cancelled_lot(self):
    response = self.app.get('/tenders/{}/lots'.format(self.tender_id))
    lot = response.json['data'][0]

    # Create cancellation on lot
    response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(self.tender_id,
                                                                                  self.tender_token),
                                  {'data': {'reason': 'cancellation reason',
                                            'cancellationOf': 'lot',
                                            'relatedLot': lot['id']}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.json['data']['status'], 'pending')

    response = self.app.get('/tenders/{}/contracts'.format(self.tender_id))
    contract = response.json['data'][0]

    # time travel
    tender = self.db.get(self.tender_id)
    for i in tender.get('awards', []):
        if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
            i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
    self.db.save(tender)

    # Try to sign (activate) contract
    response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, contract['id'],
                                                                                  self.tender_token),
                                   {'data': {'status': 'active'}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(response.json['errors'][0]["description"],
                     "Can\'t update contract while cancellation for corresponding lot exists", )


# TenderNegotiationLot2ContractResourceTest
def sign_second_contract(self):
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


def create_two_contract(self):
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


# TenderNegotiationQuickAccelerationTest
@unittest.skipUnless(SANDBOX_MODE, "not supported accelerator")
def create_tender_contract_negotiation_quick(self):
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


# TenderContractDocumentResourceTest
def not_found(self):
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


def create_tender_contract_document(self):
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


def put_tender_contract_document(self):
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


def patch_tender_contract_document(self):
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


# TenderMergedContracts2LotsResourceTest
def not_found_contract_for_award_2(self):
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
         'description': ['Can\'t found contract for award {}'.format(second_award_id)]}
    ])


def try_merge_not_real_award_2(self):
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
        {u'location': u'body', u'name': u'additionalAwardIDs', u'description': [u'id must be one of award id']}
    ])


def try_merge_itself_2(self):
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
    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'additionalAwardIDs': [first_contract['awardID']]}}, status=422
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['422'])
    self.assertEqual(response.json['errors'], [
        {'location': 'body', 'name': 'additionalAwardIDs', 'description': ['Can\'t merge itself']}
    ])


def standstill_period_2(self):
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

    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'additionalAwardIDs': additionalAwardIDs}}
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']
    self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
    self.assertEqual(first_contract['id'], second_contract['mergedInto'])
    self.assertEqual(second_contract['status'], 'merged')

    # Update complaintPeriod for additional award
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

    dateSigned = get_now().isoformat()

    # Try set status active for main contract
    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'status': 'active'}}, status=200
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

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


def activate_contract_with_complaint_2(self):
    first_award, second_award = self.create_awards()
    first_award_id = first_award['id']
    second_award_id = second_award['id']

    self.active_awards(first_award_id, second_award_id)

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']

    additionalAwardIDs = [second_contract['awardID']]

    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'additionalAwardIDs': additionalAwardIDs}}
    )
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
    self.assertEqual(response.status, self.RESPONSE_CODE['201'])

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
        {'data': {'dateSigned': get_now().isoformat(), 'status': 'active'}}, status=200
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Lets resolve complaint
    data = {'data': {'status': 'answered', 'resolutionType': 'resolved', 'resolution': 'resolution text ' * 2}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id, second_contract['awardID'], complaint['id'], self.tender_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]['description'], 'Forbidden')

    data = {'data': {'status': 'resolved', 'satisfied': True}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id, second_contract['awardID'], complaint['id'], owner_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['errors'][0]['description'], 'Can\'t update complaint')

    # Try sign contract again
    dateSigned = get_now().isoformat()
    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'dateSigned': dateSigned, 'status': 'active'}}
    )
    self.assertEqual(response.json['data']['status'], 'active')
    self.assertEqual(response.json['data']['dateSigned'], dateSigned)


def cancel_award_2(self):
    """Create two awards and merged them and then cancel additional award"""
    first_award, second_award = self.create_awards()
    first_award_id = first_award['id']
    second_award_id = second_award['id']

    self.active_awards(first_award_id, second_award_id)

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']

    additionalAwardIDs = [second_contract['awardID']]

    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'additionalAwardIDs': additionalAwardIDs}}
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']
    self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
    self.assertEqual(first_contract['id'], second_contract['mergedInto'])
    self.assertEqual(second_contract['status'], 'merged')

    # Cancel additional award
    self.assertEqual(first_contract['status'], 'pending')

    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_award_id, self.tender_token),
        {'data': {'status': 'cancelled'}}, status=200
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, second_award_id, self.tender_token),
        {'data': {'status': 'cancelled'}}, status=422
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['422'])
    self.assertEqual(
        response.json['errors'][0]['description'][0]['additionalAwardIDs'], ['awards must has status active']
    )


def cancel_main_award_2(self):
    """Create two awards and merged them and then cancel main award"""
    first_award, second_award = self.create_awards()
    first_award_id = first_award['id']
    second_award_id = second_award['id']

    self.active_awards(first_award_id, second_award_id)

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']

    additionalAwardIDs = [second_contract['awardID']]

    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'additionalAwardIDs': additionalAwardIDs}}
    )
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
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 2)
    self.assertIn('additionalAwardIDs', response.json['data'][0])
    self.assertEqual(response.json['data'][1]['status'], 'merged')

    # Check that new award was created and has status pending
    response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 2)
    self.assertEqual(response.json['data'][-1]['status'], 'active')


def merge_two_contracts_with_different_supliers_ids_2(self):
    """Try merge contracts with different suppliers"""
    self.app.authorization = ('Basic', ('token', ''))

    # Create two awards
    first_lot_response = self.app.post_json(
        '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
        {'data': test_lots[0]}
    )

    second_lot_response = self.app.post_json(
        '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
        {'data': test_lots[0]}
    )

    first_award_response = self.app.post_json(
        '/tenders/{}/awards'.format(self.tender_id),
        {'data': {
            'suppliers': [test_organization],
            'status': 'pending',
            'value': first_lot_response.json['data']['value'],
            'lotID': first_lot_response.json['data']['id']
        }}
    )

    test_organization['identifier']['id'] = '1111111'

    second_award_response = self.app.post_json(
        '/tenders/{}/awards'.format(self.tender_id),
        {'data': {
            'suppliers': [test_organization],
            'status': 'pending',
            'value': second_lot_response.json['data']['value'],
            'lotID': second_lot_response.json['data']['id']
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
    self.assertEqual(response.json['errors'], [
        {'location': 'body', 'name': 'additionalAwardIDs', 'description': ['Awards must have same suppliers id']}
    ])

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']

    self.assertNotIn('additionalAwardIDs', first_contract)
    self.assertNotIn('mergedInto', second_contract)
    self.assertNotEqual(second_contract['status'], 'merged')


def merge_two_contracts_with_different_suppliers_scheme_2(self):
    self.app.authorization = ('Basic', ('token', ''))

    # Set different scheme
    # Create two awards
    first_lot_response = self.app.post_json(
        '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
        {'data': test_lots[0]}
    )

    second_lot_response = self.app.post_json(
        '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
        {'data': test_lots[0]}
    )

    test_organization['identifier']['scheme'] = 'UA-EDR'

    first_award_response = self.app.post_json(
        '/tenders/{}/awards'.format(self.tender_id),
        {'data': {
            'suppliers': [test_organization],
            'status': 'pending',
            'value': first_lot_response.json['data']['value'],
            'lotID': first_lot_response.json['data']['id']
        }}
    )

    test_organization['identifier']['scheme'] = 'LV-RE'

    second_award_response = self.app.post_json(
        '/tenders/{}/awards'.format(self.tender_id),
        {'data': {
            'suppliers': [test_organization],
            'status': 'pending',
            'value': second_lot_response.json['data']['value'],
            'lotID': second_lot_response.json['data']['id']
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


def set_big_value_2(self):
    """Create two awards and merged them"""
    first_award, second_award = self.create_awards()
    first_award_id = first_award['id']
    second_award_id = second_award['id']

    self.active_awards(first_award_id, second_award_id)

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']

    additionalAwardIDs = [second_contract['awardID']]

    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'additionalAwardIDs': additionalAwardIDs}}
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']
    self.assertEqual(first_contract['additionalAwardIDs'], additionalAwardIDs)
    self.assertEqual(first_contract['id'], second_contract['mergedInto'])
    self.assertEqual(second_contract['status'], 'merged')

    response = self.app.get(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token)
    )

    max_value =first_award['value']['amount'] + second_award['value']['amount']

    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'value': {'amount': max_value + 0.1}}}, status=403
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(
        response.json['errors'][0]['description'],
        u'Value amount should be less or equal to awarded amount ({value:.1f})'.format(value=max_value)
    )


# TenderMergedContracts3LotsResourceTest
def merge_three_contracts_3(self):
    """Create three awards and merged them"""

    first_award, second_award, third_award = self.create_awards()

    first_award_id = first_award['id']
    second_award_id = second_award['id']
    third_award_id = third_award['id']

    self.active_awards(first_award_id, second_award_id, third_award_id)

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
    self.assertEqual(response.json['data']['status'], 'active')


def standstill_period_3(self):
    """
    Create three awards and merged them and try set status active for main
    contract while additional award has stand still period
    """

    # Create and active awards
    first_award, second_award, third_award = self.create_awards()

    first_award_id = first_award['id']
    second_award_id = second_award['id']
    third_award_id = third_award['id']

    self.active_awards(first_award_id, second_award_id, third_award_id)

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
        "startDate": (now + timedelta(days=1)).isoformat(),
        "endDate": (now + timedelta(days=1)).isoformat()
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

    dateSigned = get_now().isoformat()

    # Try set status active for main contract
    response = self.app.patch_json(
        '/tenders/{}/contracts/{}?acc_token={}'.format(self.tender_id, first_contract['id'], self.tender_token),
        {'data': {'status': 'active'}}, status=403
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertIn(
        'Can\'t sign contract before stand-still period end',
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


def activate_contract_with_complaint_3(self):
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

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
        {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=200
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Lets resolve first complaint
    data = {'data': {'status': 'answered', 'resolutionType': 'resolved', 'resolution': 'resolution text'}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id, second_contract['awardID'], second_award_complaint['id'], self.tender_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Forbidden')

    data = {"data": {"satisfied": True, "status": "resolved"}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id,
            second_contract['awardID'],
            second_award_complaint['id'],
            second_award_complaint_owner_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Can\'t update complaint')

    # Try set status active for main contract again
    response = self.app.patch_json(
        "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
        {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=200
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Lets resolve second complaint
    data = {'data': {'status': 'answered', 'resolutionType': 'resolved', 'resolution': 'resolution text'}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id, third_contract['awardID'], third_award_complaint['id'], self.tender_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Forbidden')

    data = {"data": {"satisfied": True, "status": "resolved"}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id,
            third_contract['awardID'],
            third_award_complaint['id'],
            third_award_complaint_owner_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Can\'t update complaint')

    # And try sign contract again
    dateSigned = get_now().isoformat()
    response = self.app.patch_json(
        "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
        {"data": {"dateSigned": dateSigned, "status": "active"}}
    )

    self.assertEqual(response.json['data']['status'], 'active')
    self.assertEqual(response.json['data']['dateSigned'], dateSigned)


def cancel_award_3(self):
    """Create three awards and merged them and try to cancel both"""
    first_award, second_award, third_award = self.create_awards()

    first_award_id = first_award['id']
    second_award_id = second_award['id']
    third_award_id = third_award['id']

    self.active_awards(first_award_id, second_award_id, third_award_id)

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
    self.assertEqual(first_contract['status'], 'pending')

    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_award_id, self.tender_token),
        {'data': {'status': 'cancelled'}}, status=200
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, second_award_id, self.tender_token),
        {'data': {'status': 'cancelled'}}, status=422
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['422'])
    self.assertEqual(
        response.json['errors'][0]['description'][0]['additionalAwardIDs'], ['awards must has status active']
    )

    # Check main contract
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 3)
    self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 2)

    # Cancel second additional award
    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, third_contract['awardID'], self.tender_token),
        {'data': {'status': 'cancelled'}}, status=422
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['422'])

    # Check main contract
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 3)
    self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 2)


def cancel_main_award_3(self):
    """Create two awards and merged them and then cancel main contract"""
    first_award, second_award, third_award = self.create_awards()

    first_award_id = first_award['id']
    second_award_id = second_award['id']
    third_award_id = third_award['id']

    self.active_awards(first_award_id, second_award_id, third_award_id)

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
    self.assertEqual(response.json['data'][1]['status'], 'merged')
    self.assertEqual(response.json['data'][2]['status'], 'merged')

    # Check that new awards were created and has status active
    response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 3)
    self.assertEqual(response.json['data'][-1]['status'], 'active')


def try_merge_pending_award_3(self):
    first_award, second_award, third_award = self.create_awards()

    first_award_id = first_award['id']
    second_award_id = second_award['id']
    third_award_id = third_award['id']

    self.active_awards(first_award_id, second_award_id)

    # Get created contracts
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_contract, second_contract = response.json['data']

    # For third award didn't create contract
    additionalAwardIDs = [second_contract['awardID'], third_award_id]

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


def additional_awards_dateSigned_3(self):
    """Try set dateSigned before end complaint period for additional awards"""

    first_award, second_award, third_award = self.create_awards()

    first_award_id = first_award['id']
    second_award_id = second_award['id']
    third_award_id = third_award['id']

    self.active_awards(first_award_id, second_award_id, third_award_id)

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


# TenderMergedContracts4LotsResourceTest
def merge_four_contracts_4(self):
    """Create four awards and merged them"""
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    additionalAwardIDs = awards_id[1:]

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


def sign_contract_4(self):
    """Create four awards and merged them and sign main contracts"""
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    additionalAwardIDs = awards_id[1:]

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
    self.assertEqual(response.json['data']['status'], 'active')


def cancel_award_4(self):
    """Create two awards and merged them and try to cancel both"""
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    additionalAwardIDs = awards_id[1:]

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
        {'data': {'status': 'cancelled'}}, status=422
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['422'])
    self.assertEqual(
        response.json['errors'][0]['description'][0]['additionalAwardIDs'],
        ['awards must has status active']
    )

    # Check main contract
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 4)
    self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 3)

    # Cancel second additional award
    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, first_contract['awardID'], self.tender_token),
        {'data': {'status': 'cancelled'}}
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Check main contract
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 4)
    self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 3)

    # Cancel third additional award
    response = self.app.patch_json(
        '/tenders/{}/awards/{}?acc_token={}'.format(self.tender_id, fourth_contract['awardID'], self.tender_token),
        {'data': {'status': 'cancelled'}}, status=422
    )

    self.assertEqual(response.status, self.RESPONSE_CODE['422'])
    self.assertEqual(
        response.json['errors'][0]['description'][0]['additionalAwardIDs'],
        ['awards must has status active']
    )

    # Check main contract
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 4)
    self.assertEqual(len(response.json['data'][0]['additionalAwardIDs']), 3)


def cancel_main_award_4(self):
    """Create four awards and merged them and then main"""
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    additionalAwardIDs = awards_id[1:]

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
    self.assertIn('additionalAwardIDs', response.json['data'])

    # Check contracts
    response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 4)
    self.assertEqual('merged', response.json['data'][1]['status'])
    self.assertEqual('merged', response.json['data'][2]['status'])
    self.assertEqual('merged', response.json['data'][3]['status'])
    self.assertIn('mergedInto', response.json['data'][1])
    self.assertIn('mergedInto', response.json['data'][2])
    self.assertIn('mergedInto', response.json['data'][3])

    # Check that new awards were created and have status pending
    response = self.app.get('/tenders/{}/awards?acc_token={}'.format(self.tender_id, self.tender_token))

    self.assertEqual(response.status, self.RESPONSE_CODE['200'])
    self.assertEqual(len(response.json['data']), 4)
    self.assertEqual(response.json['data'][-1]['status'], 'active')


def cancel_first_main_award_4(self):
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_additionalAwardIDs = [awards_id[1]]
    second_additionalAwardIDs = [awards_id[3]]

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
    self.assertEqual(second_contract['status'], 'merged')
    self.assertIn('additionalAwardIDs', first_contract)
    self.assertIn('mergedInto', second_contract)
    self.assertEqual(third_contract['additionalAwardIDs'], second_additionalAwardIDs)
    self.assertEqual(third_contract['status'], 'pending')
    self.assertEqual(fourth_contract['status'], 'merged')
    self.assertEqual(fourth_contract['mergedInto'], third_contract['id'])


def merge_by_two_contracts_4(self):
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_additionalAwardIDs = [awards_id[1]]
    second_additionalAwardIDs = [awards_id[3]]

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
    self.assertEqual(response.json['data']['status'], 'active')


def try_merge_main_contract_4(self):
    """Try merge contract which has additionalAwardIDs"""
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_additionalAwardIDs = [awards_id[1]]

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


def try_merge_contract_two_times_4(self):
    """ Check that we can merge contract 2 times in different contracts """
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_additionalAwardIDs = [awards_id[1]]
    second_additionalAwardIDs = [awards_id[3]]

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
    first_additionalAwardIDs.append(awards_id[3])
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


def activate_contract_with_complaint_4(self):
    """" Try activate main contract while additional wards has complaints """
    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_additionalAwardIDs = [awards_id[1]]
    second_additionalAwardIDs = [awards_id[3]]

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
        {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=200
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Try set status active for second main contract
    response = self.app.patch_json(
        "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, first_contract['id'], self.tender_token),
        {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=200
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Lets resolve first complaint
    data = {'data': {'status': 'answered', 'resolutionType': 'resolved', 'resolution': 'resolution text'}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id, second_contract['awardID'], second_award_complaint['id'], self.tender_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Forbidden')

    data = {"data": {"satisfied": True, "status": "resolved"}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id,
            second_contract['awardID'],
            second_award_complaint['id'],
            second_award_complaint_owner_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Can\'t update complaint')

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
        {"data": {"dateSigned": get_now().isoformat(), "status": "active"}}, status=200
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['200'])

    # Lets resolve second complaint
    data = {'data': {'status': 'answered', 'resolutionType': 'resolved', 'resolution': 'resolution text'}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id, fourth_contract['awardID'], fourth_award_complaint['id'], self.tender_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Forbidden')

    data = {"data": {"satisfied": True, "status": "resolved"}}
    response = self.app.patch_json(
        '/tenders/{}/awards/{}/complaints/{}?acc_token={}'.format(
            self.tender_id,
            fourth_contract['awardID'],
            fourth_award_complaint['id'],
            fourth_award_complaint_owner_token
        ), data, status=403
    )
    self.assertEqual(response.status, self.RESPONSE_CODE['403'])
    self.assertEqual(response.json['errors'][0]['description'], 'Can\'t update complaint')

    # And try sign contract again
    dateSigned = get_now().isoformat()
    response = self.app.patch_json(
        "/tenders/{}/contracts/{}?acc_token={}".format(self.tender_id, third_contract['id'], self.tender_token),
        {"data": {"dateSigned": dateSigned, "status": "active"}}
    )

    self.assertEqual(response.json['data']['status'], 'active')
    self.assertEqual(response.json['data']['dateSigned'], dateSigned)


def additional_awards_dateSigned_4(self):
    """ Try set dateSigned before end complaint period for additional awards """

    awards = [award for award in self.create_awards()]
    awards_id = [award['id'] for award in awards]

    self.active_awards(*awards_id)

    # Get created contracts
    contract_response = self.app.get('/tenders/{}/contracts?acc_token={}'.format(self.tender_id, self.tender_token))
    first_additionalAwardIDs = [awards_id[1]]
    second_additionalAwardIDs = [awards_id[3]]

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
