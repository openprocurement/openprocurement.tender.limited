# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy
from uuid import uuid4

from openprocurement.api import ROUTE_PREFIX
from openprocurement.api.models import get_now
from openprocurement.tender.limited.models import (NegotiationTender,
                                                   NegotiationQuickTender,
                                                   ReportingTender)
from openprocurement.tender.limited.tests.base import (
    test_tender_data, test_tender_negotiation_data,
    test_tender_negotiation_quick_data, BaseTenderWebTest,
    test_organization,
)


class TenderTest(BaseTenderWebTest):

    def test_simple_add_tender(self):
        u = ReportingTender(test_tender_data)
        u.tenderID = "UA-X"

        assert u.id is None
        assert u.rev is None

        u.store(self.db)

        assert u.id is not None
        assert u.rev is not None

        fromdb = self.db.get(u.id)

        assert u.tenderID == fromdb['tenderID']
        assert u.doc_type == "Tender"
        assert u.procurementMethodType == "reporting"
        assert u.procurementMethodType == fromdb['procurementMethodType']

        u.delete_instance(self.db)


class TenderNegotiationTest(BaseTenderWebTest):
    initial_data = test_tender_negotiation_data

    def test_simple_add_tender(self):
        u = NegotiationTender(test_tender_negotiation_data)
        u.tenderID = "UA-X"

        assert u.id is None
        assert u.rev is None

        u.store(self.db)

        assert u.id is not None
        assert u.rev is not None

        fromdb = self.db.get(u.id)

        assert u.tenderID == fromdb['tenderID']
        assert u.doc_type == "Tender"
        assert u.procurementMethodType == "negotiation"
        assert u.procurementMethodType == fromdb['procurementMethodType']

        u.delete_instance(self.db)


class TenderNegotiationQuickTest(TenderNegotiationTest):
    initial_data = test_tender_negotiation_quick_data

    def test_simple_add_tender(self):
        u = NegotiationQuickTender(test_tender_negotiation_quick_data)
        u.tenderID = "UA-X"

        assert u.id is None
        assert u.rev is None

        u.store(self.db)

        assert u.id is not None
        assert u.rev is not None

        fromdb = self.db.get(u.id)

        assert u.tenderID == fromdb['tenderID']
        assert u.doc_type == "Tender"
        assert u.procurementMethodType == "negotiation.quick"
        assert u.procurementMethodType == fromdb['procurementMethodType']

        u.delete_instance(self.db)


class TenderResourceTest(BaseTenderWebTest):

    def test_empty_listing(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], [])
        self.assertNotIn('{\n    "', response.body)
        self.assertNotIn('callback({', response.body)
        self.assertEqual(response.json['next_page']['offset'], '')
        self.assertNotIn('prev_page', response.json)

        response = self.app.get('/tenders?opt_jsonp=callback')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/javascript')
        self.assertNotIn('{\n    "', response.body)
        self.assertIn('callback({', response.body)

        response = self.app.get('/tenders?opt_pretty=1')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "', response.body)
        self.assertNotIn('callback({', response.body)

        response = self.app.get('/tenders?opt_jsonp=callback&opt_pretty=1')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/javascript')
        self.assertIn('{\n    "', response.body)
        self.assertIn('callback({', response.body)

        response = self.app.get('/tenders?offset=2015-01-01T00:00:00+02:00&descending=1&limit=10')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], [])
        self.assertIn('descending=1', response.json['next_page']['uri'])
        self.assertIn('limit=10', response.json['next_page']['uri'])
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertIn('limit=10', response.json['prev_page']['uri'])

        response = self.app.get('/tenders?feed=changes')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], [])
        self.assertEqual(response.json['next_page']['offset'], '')
        self.assertNotIn('prev_page', response.json)

        response = self.app.get('/tenders?feed=changes&offset=0', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Offset expired/invalid', u'location': u'params', u'name': u'offset'}
        ])

        response = self.app.get('/tenders?feed=changes&descending=1&limit=10')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], [])
        self.assertIn('descending=1', response.json['next_page']['uri'])
        self.assertIn('limit=10', response.json['next_page']['uri'])
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertIn('limit=10', response.json['prev_page']['uri'])

    def test_listing(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        tenders = []

        for i in range(3):
            offset = get_now().isoformat()
            response = self.app.post_json('/tenders', {'data': self.initial_data})
            self.assertEqual(response.status, '201 Created')
            self.assertEqual(response.content_type, 'application/json')
            tenders.append(response.json['data'])


        ids = ','.join([i['id'] for i in tenders])

        while True:
            response = self.app.get('/tenders')
            self.assertTrue(ids.startswith(','.join([i['id'] for i in response.json['data']])))
            if len(response.json['data']) == 3:
                break

        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified']))
        self.assertEqual(set([i['id'] for i in response.json['data']]), set([i['id'] for i in tenders]))
        self.assertEqual(set([i['dateModified'] for i in response.json['data']]), set([i['dateModified'] for i in tenders]))
        self.assertEqual([i['dateModified'] for i in response.json['data']], sorted([i['dateModified'] for i in tenders]))

        while True:
            response = self.app.get('/tenders?offset={}'.format(offset))
            self.assertEqual(response.status, '200 OK')
            if len(response.json['data']) == 1:
                break
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get('/tenders?limit=2')
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('prev_page', response.json)
        self.assertEqual(len(response.json['data']), 2)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.get('/tenders', params=[('opt_fields', 'status')])
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified', u'status']))
        self.assertIn('opt_fields=status', response.json['next_page']['uri'])

        response = self.app.get('/tenders', params=[('opt_fields', 'status')])
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified', u'status']))
        self.assertIn('opt_fields=status', response.json['next_page']['uri'])

        response = self.app.get('/tenders?descending=1')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified']))
        self.assertEqual(set([i['id'] for i in response.json['data']]), set([i['id'] for i in tenders]))
        self.assertEqual([i['dateModified'] for i in response.json['data']], sorted([i['dateModified'] for i in tenders], reverse=True))

        response = self.app.get('/tenders?descending=1&limit=2')
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 2)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 0)

        test_tender_data2 = self.initial_data.copy()
        test_tender_data2['mode'] = 'test'
        response = self.app.post_json('/tenders', {'data': test_tender_data2})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        while True:
            response = self.app.get('/tenders?mode=test')
            self.assertEqual(response.status, '200 OK')
            if len(response.json['data']) == 1:
                break
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get('/tenders?mode=_all_')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 4)

    def test_listing_changes(self):
        response = self.app.get('/tenders?feed=changes')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        tenders = []

        for i in range(3):
            response = self.app.post_json('/tenders', {'data': self.initial_data})
            self.assertEqual(response.status, '201 Created')
            self.assertEqual(response.content_type, 'application/json')
            tenders.append(response.json['data'])

        ids = ','.join([i['id'] for i in tenders])

        while True:
            response = self.app.get('/tenders?feed=changes')
            self.assertTrue(ids.startswith(','.join([i['id'] for i in response.json['data']])))
            if len(response.json['data']) == 3:
                break

        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified']))
        self.assertEqual(set([i['id'] for i in response.json['data']]), set([i['id'] for i in tenders]))
        self.assertEqual(set([i['dateModified'] for i in response.json['data']]), set([i['dateModified'] for i in tenders]))
        self.assertEqual([i['dateModified'] for i in response.json['data']], sorted([i['dateModified'] for i in tenders]))

        response = self.app.get('/tenders?feed=changes&limit=2')
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('prev_page', response.json)
        self.assertEqual(len(response.json['data']), 2)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.get('/tenders?feed=changes', params=[('opt_fields', 'status')])
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified', u'status']))
        self.assertIn('opt_fields=status', response.json['next_page']['uri'])

        response = self.app.get('/tenders?feed=changes', params=[('opt_fields', 'status,enquiryPeriod')])
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified', u'status']))
        self.assertIn('opt_fields=status', response.json['next_page']['uri'])

        response = self.app.get('/tenders?feed=changes&descending=1')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified']))
        self.assertEqual(set([i['id'] for i in response.json['data']]), set([i['id'] for i in tenders]))
        self.assertEqual([i['dateModified'] for i in response.json['data']], sorted([i['dateModified'] for i in tenders], reverse=True))

        response = self.app.get('/tenders?feed=changes&descending=1&limit=2')
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 2)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get(response.json['next_page']['path'].replace(ROUTE_PREFIX, ''))
        self.assertEqual(response.status, '200 OK')
        self.assertNotIn('descending=1', response.json['prev_page']['uri'])
        self.assertEqual(len(response.json['data']), 0)

        test_tender_data2 = self.initial_data.copy()
        test_tender_data2['mode'] = 'test'
        response = self.app.post_json('/tenders', {'data': test_tender_data2})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')

        while True:
            response = self.app.get('/tenders?feed=changes&mode=test')
            self.assertEqual(response.status, '200 OK')
            if len(response.json['data']) == 1:
                break
        self.assertEqual(len(response.json['data']), 1)

        response = self.app.get('/tenders?feed=changes&mode=_all_')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 4)

    def test_listing_draft(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        tenders = []
        data = test_tender_data.copy()
        data.update({'status': 'draft'})

        for i in range(3):
            response = self.app.post_json('/tenders', {'data': test_tender_data})
            self.assertEqual(response.status, '201 Created')
            self.assertEqual(response.content_type, 'application/json')
            tenders.append(response.json['data'])
            response = self.app.post_json('/tenders', {'data': data})
            self.assertEqual(response.status, '201 Created')
            self.assertEqual(response.content_type, 'application/json')

        ids = ','.join([i['id'] for i in tenders])

        while True:
            response = self.app.get('/tenders')
            self.assertTrue(ids.startswith(','.join([i['id'] for i in response.json['data']])))
            if len(response.json['data']) == 3:
                break

        self.assertEqual(len(response.json['data']), 3)
        self.assertEqual(set(response.json['data'][0]), set([u'id', u'dateModified']))
        self.assertEqual(set([i['id'] for i in response.json['data']]), set([i['id'] for i in tenders]))
        self.assertEqual(set([i['dateModified'] for i in response.json['data']]), set([i['dateModified'] for i in tenders]))
        self.assertEqual([i['dateModified'] for i in response.json['data']], sorted([i['dateModified'] for i in tenders]))

    def test_create_tender_invalid(self):
        request_path = '/tenders'
        response = self.app.post(request_path, 'data', status=415)
        self.assertEqual(response.status, '415 Unsupported Media Type')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description':
                u"Content-Type header should be one of ['application/json']", u'location': u'header', u'name': u'Content-Type'}
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

        response = self.app.post_json(request_path, {'not_data': {}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Data not available',
                u'location': u'body', u'name': u'data'}
        ])

        response = self.app.post_json(request_path, {'data': []}, status=422)
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

        response = self.app.post_json(request_path, {'data': {'value': 'invalid_value'}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [
                u'Please use a mapping for this field or Value instance instead of unicode.'], u'location': u'body', u'name': u'value'}
        ])

        response = self.app.post_json(request_path, {'data': {'procurementMethod': 'invalid_value'}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertIn({u'description': [u"Value must be one of ['open', 'selective', 'limited']."], u'location': u'body', u'name': u'procurementMethod'}, response.json['errors'])
        self.assertIn({u'description': [u'This field is required.'], u'location': u'body', u'name': u'tenderPeriod'}, response.json['errors'])
        self.assertIn({u'description': [u'This field is required.'], u'location': u'body', u'name': u'minimalStep'}, response.json['errors'])
        self.assertIn({u'description': [u'This field is required.'], u'location': u'body', u'name': u'items'}, response.json['errors'])
        self.assertIn({u'description': [u'This field is required.'], u'location': u'body', u'name': u'enquiryPeriod'}, response.json['errors'])
        self.assertIn({u'description': [u'This field is required.'], u'location': u'body', u'name': u'value'}, response.json['errors'])
        self.assertIn({u'description': [u'This field is required.'], u'location': u'body', u'name': u'items'}, response.json['errors'])

        response = self.app.post_json(request_path, {'data': {'enquiryPeriod': {'endDate': 'invalid_value'}}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': {u'endDate': [u"Could not parse invalid_value. Should be ISO8601."]}, u'location': u'body', u'name': u'enquiryPeriod'}
        ])

        data = self.initial_data["items"][0]["additionalClassifications"][0]["scheme"]
        self.initial_data["items"][0]["additionalClassifications"][0]["scheme"] = 'Не ДКПП'
        response = self.app.post_json(request_path, {'data': self.initial_data}, status=422)
        self.initial_data["items"][0]["additionalClassifications"][0]["scheme"] = data
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'additionalClassifications': [u"One of additional classifications should be one of [ДКПП, NONE, ДК003, ДК015, ДК018]."]}], u'location': u'body', u'name': u'items'}
        ])

        data = self.initial_data["procuringEntity"]["contactPoint"]["telephone"]
        del self.initial_data["procuringEntity"]["contactPoint"]["telephone"]
        response = self.app.post_json(request_path, {'data': self.initial_data}, status=422)
        self.initial_data["procuringEntity"]["contactPoint"]["telephone"] = data
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': {u'contactPoint': {u'email': [u'telephone or email should be present']}}, u'location': u'body', u'name': u'procuringEntity'}
        ])

        data = self.initial_data["items"][0].copy()
        classification = data['classification'].copy()
        classification["id"] = u'19212310-1'
        data['classification'] = classification
        self.initial_data["items"] = [self.initial_data["items"][0], data]
        response = self.app.post_json(request_path, {'data': self.initial_data}, status=422)
        self.initial_data["items"] = self.initial_data["items"][:1]
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'CPV group of items be identical'], u'location': u'body', u'name': u'items'}
        ])

        data = deepcopy(test_tender_data)
        del data["items"][0]['deliveryAddress']['postalCode']
        del data["items"][0]['deliveryAddress']['locality']
        del data["items"][0]['deliveryDate']
        response = self.app.post_json(request_path, {'data': data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [{u'deliveryDate': [u'This field is required.'], u'deliveryAddress': {u'postalCode': [u'This field is required.'], u'locality': [u'This field is required.']}}], u'location': u'body', u'name': u'items'}
        ])
        
        data = deepcopy(test_tender_data)
        data['items'][0]['relatedLot'] = uuid4().hex
        response = self.app.post_json(request_path, {'data':data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'],  [
            {u'description': [{u'relatedLot': [u'This option is not available']}], u'location': u'body', u'name': u'items'}])
        
    def test_create_tender_generated(self):
        data = self.initial_data.copy()
        data.update({'id': 'hash', 'doc_id': 'hash2', 'tenderID': 'hash3'})
        response = self.app.post_json('/tenders', {'data': data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        fields = [u'id', u'dateModified', u'tenderID', u'status', u'items',
                  u'value', u'procuringEntity', u'owner', u'procurementMethod',
                  u'procurementMethodType', u'title', u'date']
        if u'procurementMethodDetails' in self.initial_data:
            fields.append(u'procurementMethodDetails')
        if "negotiation" == self.initial_data['procurementMethodType']:
            fields.append(u'cause')
        if "negotiation" in self.initial_data['procurementMethodType']:
            fields.append(u'causeDescription')
        self.assertEqual(set(tender), set(fields))
        self.assertNotEqual(data['id'], tender['id'])
        self.assertNotEqual(data['doc_id'], tender['id'])
        self.assertNotEqual(data['tenderID'], tender['tenderID'])

    def test_create_tender_draft(self):
        data = self.initial_data.copy()
        data.update({'status': 'draft'})
        response = self.app.post_json('/tenders', {'data': data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        owner_token = response.json['access']['token']
        self.assertEqual(tender['status'], 'draft')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'value': {'amount': 100}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u"Can't update tender in current (draft) status", u'location': u'body', u'name': u'data'}
        ])

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'status': 'active'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'active')

        response = self.app.get('/tenders/{}'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'active')

    def test_create_tender(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.post_json('/tenders', {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        tender_set = set(tender)
        if 'procurementMethodDetails' in tender_set:
            tender_set.remove('procurementMethodDetails')
        if "negotiation" == self.initial_data['procurementMethodType']:
            tender_set.remove(u'cause')
        if "negotiation" in self.initial_data['procurementMethodType']:
            tender_set.remove(u'causeDescription')
        self.assertEqual(tender_set - set(test_tender_data), set(
            [u'id', u'date', u'dateModified', u'owner', u'tenderID', u'status', u'procurementMethod']))
        self.assertIn(tender['id'], response.headers['Location'])

        response = self.app.get('/tenders/{}'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(set(response.json['data']), set(tender))
        self.assertEqual(response.json['data'], tender)

        response = self.app.post_json('/tenders?opt_jsonp=callback', {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/javascript')
        self.assertIn('callback({"', response.body)

        response = self.app.post_json('/tenders?opt_pretty=1', {"data": self.initial_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "', response.body)

        response = self.app.post_json('/tenders', {"data": self.initial_data, "options": {"pretty": True}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "', response.body)

    def test_get_tender(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.post_json('/tenders', {'data': self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender = response.json['data']

        response = self.app.get('/tenders/{}'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], tender)

        response = self.app.get('/tenders/{}?opt_jsonp=callback'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/javascript')
        self.assertIn('callback({"data": {"', response.body)

        response = self.app.get('/tenders/{}?opt_pretty=1'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('{\n    "data": {\n        "', response.body)

    def test_patch_tender(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.post_json('/tenders', {'data': self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender = response.json['data']
        owner_token = response.json['access']['token']
        dateModified = tender.pop('dateModified')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'procurementMethodRationale': 'Limited'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        new_tender = response.json['data']
        new_dateModified = new_tender.pop('dateModified')
        tender['procurementMethodRationale'] = 'Limited'
        self.assertEqual(tender, new_tender)
        self.assertNotEqual(dateModified, new_dateModified)

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'dateModified': new_dateModified}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        new_tender2 = response.json['data']
        new_dateModified2 = new_tender2.pop('dateModified')
        self.assertEqual(new_tender, new_tender2)
        self.assertEqual(new_dateModified, new_dateModified2)

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'procuringEntity': {'kind': 'defense'}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertNotEqual(response.json['data']['procuringEntity']['kind'], 'defense')

        revisions = self.db.get(tender['id']).get('revisions')
        self.assertEqual(revisions[-1][u'changes'][0]['op'], u'remove')
        self.assertEqual(revisions[-1][u'changes'][0]['path'], u'/procurementMethodRationale')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'items': [self.initial_data['items'][0]]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'items': [{}, self.initial_data['items'][0]]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        item0 = response.json['data']['items'][0]
        item1 = response.json['data']['items'][1]
        self.assertNotEqual(item0.pop('id'), item1.pop('id'))
        self.assertEqual(item0, item1)

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'items': [{}]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(len(response.json['data']['items']), 1)

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'items': [{"classification": {
            "scheme": "CPV",
            "id": "55523100-3",
            "description": "Послуги з харчування у школах"
        }}]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'items': [{"additionalClassifications": [
            tender['items'][0]["additionalClassifications"][0] for i in range(3)
        ]}]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'items': [{"additionalClassifications": tender['items'][0]["additionalClassifications"]}]}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        # The following operations are performed for a proper transition to the "Complete" tender status

        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'suppliers': [test_organization], 'status': 'pending'}})
        award_id = response.json['data']['id']
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender['id'], award_id, owner_token),
                                       {"data": {"qualified": True, "status": "active"}})

        response = self.app.get('/tenders/{}/contracts'.format(
                tender['id']))
        contract_id = response.json['data'][0]['id']

        response = self.app.post('/tenders/{}/contracts/{}/documents?acc_token={}'.format(
            tender['id'], contract_id, owner_token), upload_files=[('file', 'name.doc', 'content')])
        self.assertEqual(response.status, '201 Created')

        save_tender = self.db.get(tender['id'])
        for i in save_tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # works for negotiation tender
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(save_tender)

        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(
            tender['id'], contract_id, owner_token), {'data': {'status': 'active'}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.get('/tenders/{}'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'complete')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'status': 'active'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update tender in current (complete) status")

    def test_dateModified_tender(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.post_json('/tenders', {'data': self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender = response.json['data']
        dateModified = tender['dateModified']
        owner_token = response.json['access']['token']

        response = self.app.get('/tenders/{}'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['dateModified'], dateModified)

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
            tender['id'], owner_token), {'data': {'procurementMethodRationale': 'Open'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertNotEqual(response.json['data']['dateModified'], dateModified)
        tender = response.json['data']
        dateModified = tender['dateModified']

        response = self.app.get('/tenders/{}'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'], tender)
        self.assertEqual(response.json['data']['dateModified'], dateModified)

    def test_tender_not_found(self):
        response = self.app.get('/tenders')
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(len(response.json['data']), 0)

        response = self.app.get('/tenders/some_id', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'tender_id'}
        ])

        response = self.app.patch_json(
            '/tenders/some_id', {'data': {}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location': u'url', u'name': u'tender_id'}
        ])

    def test_tender_Administrator_change(self):
        response = self.app.post_json('/tenders', {'data': self.initial_data})
        self.assertEqual(response.status, '201 Created')
        tender = response.json['data']

        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('administrator', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender['id']),
                                       {'data': {'mode': u'test', 'procuringEntity': {"identifier": {"id": "00000000"}}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['mode'], u'test')
        self.assertEqual(response.json['data']["procuringEntity"]["identifier"]["id"], "00000000")

        self.app.authorization = authorization

        response = self.app.post_json('/tenders', {'data': self.initial_data})
        self.assertEqual(response.status, '201 Created')

        self.app.authorization = ('Basic', ('administrator', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender['id']), {'data': {'mode': u'test'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['mode'], u'test')


class TenderNegotiationResourceTest(TenderResourceTest):
    initial_data = test_tender_negotiation_data

class TenderNegotiationQuickResourceTest(TenderNegotiationResourceTest):
    initial_data = test_tender_negotiation_quick_data

class TenderProcessTest(BaseTenderWebTest):

    def test_tender_status_change(self):
        # empty tenders listing
        response = self.app.get('/tenders')
        self.assertEqual(response.json['data'], [])
        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender_id), {'data': {'status': 'complete'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Chronograph has no power over me!")

        self.app.authorization = ('Basic', ('broker', ''))
        response = self.app.patch_json('/tenders/{}'.format(tender_id), {'data': {'status': 'complete'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        # check status
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']['status'], 'active')

        # try to mark tender complete
        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {'data': {'status': 'complete'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'active')

    def test_single_award_tender(self):
        # empty tenders listing
        response = self.app.get('/tenders')
        self.assertEqual(response.json['data'], [])
        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(response.json['data'], [])

        # create award
        response = self.app.post_json('/tenders/{}/awards'.format(tender_id),
                                      {'data': {'suppliers': [test_organization],
                                                "value": {"amount": 500}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')

        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))

        # get pending award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][0]

        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"qualified": True, "status": "active"}})

        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']

        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        # sign contract
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        # check status
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']['status'], 'complete')

        # create new tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')

        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(len(response.json['data']), 1)

        # get last award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][-1]

        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active"}})

        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract = response.json['data']['contracts'][-1]
        self.assertEqual(contract['awardID'], award_id)

        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        # set award to cancelled
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token),
                                       {"data": {"status": "cancelled"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['status'], 'cancelled')

        # try to sign contract
        response = self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract['id'], owner_token),
                                       {"data": {"status": "active"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update contract in current (cancelled) status")

        # tender status remains the same
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']['status'], 'active')

    def test_multiple_awards_tender(self):
        # empty tenders listing
        response = self.app.get('/tenders')
        self.assertEqual(response.json['data'], [])
        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(response.json['data'], [])

        # create award
        response = self.app.post_json('/tenders/{}/awards'.format(tender_id),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 500}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        award = response.json['data']

        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award['id'], owner_token),
                            {"data": {"qualified": True, "status": "active"}})
        self.assertEqual(response.status, '200 OK')

        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                'value': {"amount": 501}}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.json['errors'][0]["description"], "Can't create new award while any (active) award exists")

        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award['id'], owner_token),
                            {"data": {"status": "cancelled"}})

        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 505}}})
        self.assertEqual(response.status, '201 Created')

        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(len(response.json['data']), 2)

        # get last award
        award_id = [i['id'] for i in response.json['data'] if i['status'] == 'pending'][-1]

        # set award as active
        self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award_id, owner_token), {"data": {"status": "active"}})

        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract = response.json['data']['contracts'][-1]
        self.assertEqual(contract['awardID'], award_id)

        # time travel
        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # reporting procedure does not have complaintPeriod
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        # sign contract
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract['id'], owner_token), {"data": {"status": "active"}})
        # check status
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.json['data']['status'], 'complete')

    def test_tender_cancellation(self):
        # empty tenders listing
        response = self.app.get('/tenders')
        self.assertEqual(response.json['data'], [])
        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # create cancellation
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'invalid conditions',
            'status': 'active'
        }})
        self.assertEqual(response.status, '201 Created')
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'cancelled')

        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')

        # create cancellation
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'invalid conditions',
            'status': 'active'
        }})
        self.assertEqual(response.status, '201 Created')
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'cancelled')

        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(len(response.json['data']), 1)
        award = response.json['data'][0]
        self.assertEqual(award['status'], 'pending')

        # set award as active
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award['id'], owner_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']

        # create cancellation in stand still
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'invalid conditions',
            'status': 'active'
        }})
        self.assertEqual(response.status, '201 Created')
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'cancelled')

        # create tender
        response = self.app.post_json('/tenders',
                                      {"data": self.initial_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # create award
        response = self.app.post_json('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token),
                                      {'data': {'suppliers': [test_organization],
                                                "qualified": True,
                                                "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        # get awards
        response = self.app.get('/tenders/{}/awards?acc_token={}'.format(tender_id, owner_token))
        self.assertEqual(len(response.json['data']), 1)
        award = response.json['data'][0]
        self.assertEqual(award['status'], 'pending')

        # set award as active
        response = self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(tender_id, award['id'], owner_token), {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')

        # get contract id
        response = self.app.get('/tenders/{}'.format(tender_id))
        contract_id = response.json['data']['contracts'][-1]['id']

        tender = self.db.get(tender_id)
        for i in tender.get('awards', []):
            if i.get('complaintPeriod', {}):  # works for negotiation tender
                i['complaintPeriod']['endDate'] = i['complaintPeriod']['startDate']
        self.db.save(tender)

        # sign contract
        self.app.authorization = ('Basic', ('broker', ''))
        self.app.patch_json('/tenders/{}/contracts/{}?acc_token={}'.format(tender_id, contract_id, owner_token), {"data": {"status": "active"}})
        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'complete')

        # create cancellation
        response = self.app.post_json('/tenders/{}/cancellations?acc_token={}'.format(tender_id, owner_token), {'data': {
            'reason': 'invalid conditions',
            'status': 'active'
        }}, status=403)
        self.assertEqual(response.status, '403 Forbidden')

        response = self.app.get('/tenders/{}'.format(tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'complete')

class TenderNegotiationProcessTest(TenderProcessTest):
    initial_data = test_tender_negotiation_data

    def test_tender_cause(self):
        data = deepcopy(self.initial_data)
        del data['cause']
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'This field is required.'], u'location': u'body', u'name': u'cause'}
        ])

        data['cause'] = 'unexisting value'
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u"Value must be one of ['artContestIP', 'noCompetition', 'twiceUnsuccessful', 'additionalPurchase', 'additionalConstruction', 'stateLegalServices']."],
             u'location': u'body', u'name': u'cause'}
        ])

        data['cause'] = 'noCompetition'
        del data['causeDescription']
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'This field is required.'], u'location': u'body', u'name': u'causeDescription'}
        ])

        data['causeDescription'] = ''
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'String value is too short.'], u'location': u'body', u'name': u'causeDescription'}
        ])

        data['causeDescription'] = "blue pine"
        response = self.app.post_json('/tenders', {"data": data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.json['data']['causeDescription'], 'blue pine')
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender_id, owner_token), {"data": {"cause": "artContestIP"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['cause'], 'artContestIP')


class TenderNegotiationQuickProcessTest(TenderNegotiationProcessTest):
    initial_data = test_tender_negotiation_quick_data

    def test_tender_cause(self):
        data = deepcopy(self.initial_data)
        self.assertNotIn('cause', data)
        response = self.app.post_json('/tenders', {"data": data})
        self.assertEqual(response.status, '201 Created')

        data['cause'] = 'unexisting value'
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u"Value must be one of ['quick', 'artContestIP', 'noCompetition', 'twiceUnsuccessful', 'additionalPurchase', 'additionalConstruction', 'stateLegalServices']."],
             u'location': u'body', u'name': u'cause'}
        ])

        data['cause'] = 'quick'
        del data['causeDescription']
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'This field is required.'], u'location': u'body', u'name': u'causeDescription'}
        ])

        data['causeDescription'] = ''
        response = self.app.post_json('/tenders', {"data": data}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': [u'String value is too short.'], u'location': u'body', u'name': u'causeDescription'}
        ])

        data['causeDescription'] = "blue pine"
        response = self.app.post_json('/tenders', {"data": data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.json['data']['causeDescription'], 'blue pine')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderTest))
    suite.addTest(unittest.makeSuite(TenderResourceTest))
    suite.addTest(unittest.makeSuite(TenderProcessTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
