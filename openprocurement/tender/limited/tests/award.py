# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.tests.base import test_bids
from openprocurement.tender.limited.tests.base import BaseTenderContentWebTest, test_tender_data


class TenderAwardResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_bids = None

    def test_create_tender_award_invalid(self):
        request_path = '/tenders/{}/awards'.format(self.tender_id)
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

        response = self.app.post_json(request_path, {
                                      'data': {'suppliers': [{'identifier': 'invalid_value'}]}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': {u'identifier': [
                u'Please use a mapping for this field or Identifier instance instead of unicode.']}, u'location': u'body', u'name': u'suppliers'}
        ])

        response = self.app.post_json('/tenders/some_id/awards', {'data': {
                                      'suppliers': [test_tender_data["procuringEntity"]], 'bid_id': 'some_id'}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.get('/tenders/some_id/awards', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        # get tender and check status
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'active')

        # set tender status as 'complete'
        response = self.app.patch_json('/tenders/{}'.format(tender['id']), {'data': {'status': 'complete'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.post_json('/tenders/{}/awards'.format(self.tender_id),
                                      {'data': {'suppliers': [test_tender_data["procuringEntity"]],
                                                'status': 'pending'}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't create award in current (complete) tender status")

    def test_create_tender_award(self):
        request_path = '/tenders/{}/awards'.format(self.tender_id)
        response = self.app.post_json(request_path, {'data': {'suppliers': [test_tender_data["procuringEntity"]],
                                                              'status': 'pending'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        award = response.json['data']
        self.assertEqual(award['suppliers'][0]['name'], test_tender_data["procuringEntity"]['name'])
        self.assertIn('id', award)
        self.assertIn(award['id'], response.headers['Location'])

        response = self.app.get(request_path)
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data'][-1], award)

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"status": "active"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['status'], u'active')

        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['status'], u'active')

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"status": "cancelled"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['status'], u'cancelled')
        # self.assertIn('Location', response.headers)

    def test_patch_tender_award(self):
        request_path = '/tenders/{}/awards'.format(self.tender_id)
        response = self.app.post_json(request_path, {'data': {'suppliers': [test_tender_data["procuringEntity"]],
                                                              'status': u'pending', "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        award = response.json['data']

        response = self.app.patch_json('/tenders/{}/awards/some_id'.format(self.tender_id),
                                       {"data": {"status": "unsuccessful"}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'award_id'}
        ])

        response = self.app.patch_json('/tenders/some_id/awards/some_id',
                                       {"data": {"status": "unsuccessful"}}, status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"awardStatus": "unsuccessful"}}, status=422)
        self.assertEqual(response.status, '422 Unprocessable Entity')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'], [
            {"location": "body", "name": "awardStatus", "description": "Rogue field"}
        ])

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"status": "unsuccessful"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        # self.assertIn('Location', response.headers)
        # new_award_location = response.headers['Location']

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"status": "pending"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update award in current (unsuccessful) status")

        # response = self.app.get(request_path)
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')
        # self.assertEqual(len(response.json['data']), 2)
        # self.assertIn(response.json['data'][1]['id'], new_award_location)
        # new_award = response.json['data'][-1]

        # response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, new_award['id']),
                                       # {"data": {"status": "active"}})
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')

        # response = self.app.get(request_path)
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')
        # self.assertEqual(len(response.json['data']), 2)

        # response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, new_award['id']),
                                       # {"data": {"status": "cancelled"}})
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')
        # self.assertIn('Location', response.headers)

        # response = self.app.get(request_path)
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')
        # self.assertEqual(len(response.json['data']), 3)

        # get tender and check status
        response = self.app.get('/tenders/{}'.format(self.tender_id))
        self.assertEqual(response.status, '200 OK')
        tender = response.json['data']
        self.assertEqual(tender['status'], 'active')

        # set tender status as 'complete'
        response = self.app.patch_json('/tenders/{}'.format(tender['id']), {'data': {'status': 'complete'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')

        response = self.app.get('/tenders/{}/awards/{}'.format(self.tender_id, award['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["value"]["amount"], 500)

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"status": "unsuccessful"}}, status=403)
        self.assertEqual(response.status, '403 Forbidden')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['errors'][0]["description"], "Can't update award in current (complete) tender status")

    def test_patch_tender_award_unsuccessful(self):
        request_path = '/tenders/{}/awards'.format(self.tender_id)
        response = self.app.post_json(request_path, {'data': {'suppliers': [test_tender_data["procuringEntity"]],
                                                              'status': u'pending', "value": {"amount": 500}}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        award = response.json['data']

        response = self.app.patch_json('/tenders/{}/awards/{}'.format(self.tender_id, award['id']),
                                       {"data": {"status": "unsuccessful"}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        # self.assertIn('Location', response.headers)
        # new_award_location = response.headers['Location']

        # response = self.app.patch_json(new_award_location[-81:], {"data": {"status": "unsuccessful"}})
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')
        # self.assertNotIn('Location', response.headers)

        # response = self.app.get(request_path)
        # self.assertEqual(response.status, '200 OK')
        # self.assertEqual(response.content_type, 'application/json')
        # self.assertEqual(len(response.json['data']), 2)

    def test_get_tender_award(self):
        response = self.app.post_json('/tenders/{}/awards'.format(
            self.tender_id), {'data': {'suppliers': [test_tender_data["procuringEntity"]],
                                       'status': 'pending'}})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        award = response.json['data']

        response = self.app.get('/tenders/{}/awards/{}'.format(self.tender_id, award['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        award_data = response.json['data']
        self.assertEqual(award_data, award)

        response = self.app.get('/tenders/{}/awards/some_id'.format(self.tender_id), status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'award_id'}
        ])

        response = self.app.get('/tenders/some_id/awards/some_id', status=404)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['errors'], [
            {u'description': u'Not Found', u'location':
                u'url', u'name': u'tender_id'}
        ])


class TenderAwardDocumentResourceTest(BaseTenderContentWebTest):
   initial_status = 'active'
   initial_bids = None

   def setUp(self):
       super(TenderAwardDocumentResourceTest, self).setUp()
       # Create award
       response = self.app.post_json('/tenders/{}/awards'.format(
           self.tender_id), {'data': {'suppliers': [test_tender_data["procuringEntity"]], 'status': 'pending'}})
       award = response.json['data']
       self.award_id = award['id']

   def test_not_found(self):
       response = self.app.post('/tenders/some_id/awards/some_id/documents', status=404, upload_files=[
                                ('file', 'name.doc', 'content')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'tender_id'}
       ])

       response = self.app.post('/tenders/{}/awards/some_id/documents'.format(self.tender_id), status=404, upload_files=[('file', 'name.doc', 'content')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'award_id'}
       ])

       response = self.app.post('/tenders/{}/awards/{}/documents'.format(self.tender_id, self.award_id), status=404, upload_files=[
                                ('invalid_value', 'name.doc', 'content')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'body', u'name': u'file'}
       ])

       response = self.app.get('/tenders/some_id/awards/some_id/documents', status=404)
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'tender_id'}
       ])

       response = self.app.get('/tenders/{}/awards/some_id/documents'.format(self.tender_id), status=404)
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'award_id'}
       ])

       response = self.app.get('/tenders/some_id/awards/some_id/documents/some_id', status=404)
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'tender_id'}
       ])

       response = self.app.get('/tenders/{}/awards/some_id/documents/some_id'.format(self.tender_id), status=404)
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'award_id'}
       ])

       response = self.app.get('/tenders/{}/awards/{}/documents/some_id'.format(self.tender_id, self.award_id), status=404)
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'document_id'}
       ])

       response = self.app.put('/tenders/some_id/awards/some_id/documents/some_id', status=404,
                               upload_files=[('file', 'name.doc', 'content2')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'tender_id'}
       ])

       response = self.app.put('/tenders/{}/awards/some_id/documents/some_id'.format(self.tender_id), status=404,
                               upload_files=[('file', 'name.doc', 'content2')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'url', u'name': u'award_id'}
       ])

       response = self.app.put('/tenders/{}/awards/{}/documents/some_id'.format(
           self.tender_id, self.award_id), status=404, upload_files=[('file', 'name.doc', 'content2')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location': u'url', u'name': u'document_id'}
       ])

   def test_create_tender_award_document(self):
       response = self.app.post('/tenders/{}/awards/{}/documents'.format(
           self.tender_id, self.award_id), upload_files=[('file', 'name.doc', 'content')])
       self.assertEqual(response.status, '201 Created')
       self.assertEqual(response.content_type, 'application/json')
       doc_id = response.json["data"]['id']
       self.assertIn(doc_id, response.headers['Location'])
       self.assertEqual('name.doc', response.json["data"]["title"])
       key = response.json["data"]["url"].split('?')[-1]

       response = self.app.get('/tenders/{}/awards/{}/documents'.format(self.tender_id, self.award_id))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"][0]["id"])
       self.assertEqual('name.doc', response.json["data"][0]["title"])

       response = self.app.get('/tenders/{}/awards/{}/documents?all=true'.format(self.tender_id, self.award_id))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"][0]["id"])
       self.assertEqual('name.doc', response.json["data"][0]["title"])

       response = self.app.get('/tenders/{}/awards/{}/documents/{}?download=some_id'.format(
           self.tender_id, self.award_id, doc_id), status=404)
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location': u'url', u'name': u'download'}
       ])

       response = self.app.get('/tenders/{}/awards/{}/documents/{}?{}'.format(
           self.tender_id, self.award_id, doc_id, key))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/msword')
       self.assertEqual(response.content_length, 7)
       self.assertEqual(response.body, 'content')

       response = self.app.get('/tenders/{}/awards/{}/documents/{}'.format(
           self.tender_id, self.award_id, doc_id))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"]["id"])
       self.assertEqual('name.doc', response.json["data"]["title"])

       # get tender and check status
       response = self.app.get('/tenders/{}'.format(self.tender_id))
       self.assertEqual(response.status, '200 OK')
       tender = response.json['data']
       self.assertEqual(tender['status'], 'active')

       # set tender status as 'complete'
       response = self.app.patch_json('/tenders/{}'.format(tender['id']), {'data': {'status': 'complete'}})
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')

       response = self.app.post('/tenders/{}/awards/{}/documents'.format(
           self.tender_id, self.award_id), upload_files=[('file', 'name.doc', 'content')], status=403)
       self.assertEqual(response.status, '403 Forbidden')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['errors'][0]["description"], "Can't add document in current (complete) tender status")

   def test_put_tender_award_document(self):
       response = self.app.post('/tenders/{}/awards/{}/documents'.format(
           self.tender_id, self.award_id), upload_files=[('file', 'name.doc', 'content')])
       self.assertEqual(response.status, '201 Created')
       self.assertEqual(response.content_type, 'application/json')
       doc_id = response.json["data"]['id']
       self.assertIn(doc_id, response.headers['Location'])

       response = self.app.put('/tenders/{}/awards/{}/documents/{}'.format(self.tender_id, self.award_id, doc_id),
                               status=404,
                               upload_files=[('invalid_name', 'name.doc', 'content')])
       self.assertEqual(response.status, '404 Not Found')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['status'], 'error')
       self.assertEqual(response.json['errors'], [
           {u'description': u'Not Found', u'location':
               u'body', u'name': u'file'}
       ])

       response = self.app.put('/tenders/{}/awards/{}/documents/{}'.format(
           self.tender_id, self.award_id, doc_id), upload_files=[('file', 'name.doc', 'content2')])
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"]["id"])
       key = response.json["data"]["url"].split('?')[-1]

       response = self.app.get('/tenders/{}/awards/{}/documents/{}?{}'.format(
           self.tender_id, self.award_id, doc_id, key))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/msword')
       self.assertEqual(response.content_length, 8)
       self.assertEqual(response.body, 'content2')

       response = self.app.get('/tenders/{}/awards/{}/documents/{}'.format(
           self.tender_id, self.award_id, doc_id))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"]["id"])
       self.assertEqual('name.doc', response.json["data"]["title"])

       response = self.app.put('/tenders/{}/awards/{}/documents/{}'.format(
           self.tender_id, self.award_id, doc_id), 'content3', content_type='application/msword')
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"]["id"])
       key = response.json["data"]["url"].split('?')[-1]

       response = self.app.get('/tenders/{}/awards/{}/documents/{}?{}'.format(
           self.tender_id, self.award_id, doc_id, key))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/msword')
       self.assertEqual(response.content_length, 8)
       self.assertEqual(response.body, 'content3')

       # get tender and check status
       response = self.app.get('/tenders/{}'.format(self.tender_id))
       self.assertEqual(response.status, '200 OK')
       tender = response.json['data']
       self.assertEqual(tender['status'], 'active')

       # set tender status as 'complete'
       response = self.app.patch_json('/tenders/{}'.format(tender['id']), {'data': {'status': 'complete'}})
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')

       response = self.app.put('/tenders/{}/awards/{}/documents/{}'.format(
           self.tender_id, self.award_id, doc_id), upload_files=[('file', 'name.doc', 'content3')], status=403)
       self.assertEqual(response.status, '403 Forbidden')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['errors'][0]["description"], "Can't update document in current (complete) tender status")

   def test_patch_tender_award_document(self):
       response = self.app.post('/tenders/{}/awards/{}/documents'.format(
           self.tender_id, self.award_id), upload_files=[('file', 'name.doc', 'content')])
       self.assertEqual(response.status, '201 Created')
       self.assertEqual(response.content_type, 'application/json')
       doc_id = response.json["data"]['id']
       self.assertIn(doc_id, response.headers['Location'])

       response = self.app.patch_json('/tenders/{}/awards/{}/documents/{}'.format(self.tender_id, self.award_id, doc_id), {"data": {"description": "document description"}})
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"]["id"])

       response = self.app.get('/tenders/{}/awards/{}/documents/{}'.format(
           self.tender_id, self.award_id, doc_id))
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(doc_id, response.json["data"]["id"])
       self.assertEqual('document description', response.json["data"]["description"])

       # get tender and check status
       response = self.app.get('/tenders/{}'.format(self.tender_id))
       self.assertEqual(response.status, '200 OK')
       tender = response.json['data']
       self.assertEqual(tender['status'], 'active')

       # set tender status as 'complete'
       response = self.app.patch_json('/tenders/{}'.format(tender['id']), {'data': {'status': 'complete'}})
       self.assertEqual(response.status, '200 OK')
       self.assertEqual(response.content_type, 'application/json')

       response = self.app.patch_json('/tenders/{}/awards/{}/documents/{}'.format(self.tender_id, self.award_id, doc_id), {"data": {"description": "document description"}}, status=403)
       self.assertEqual(response.status, '403 Forbidden')
       self.assertEqual(response.content_type, 'application/json')
       self.assertEqual(response.json['errors'][0]["description"], "Can't update document in current (complete) tender status")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderAwardDocumentResourceTest))
    suite.addTest(unittest.makeSuite(TenderAwardResourceTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
