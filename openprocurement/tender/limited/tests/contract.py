# -*- coding: utf-8 -*-
import unittest

from openprocurement.api.constants import SANDBOX_MODE
from openprocurement.api.tests.base import snitch
from openprocurement.tender.belowthreshold.tests.base import test_organization
from openprocurement.tender.belowthreshold.tests.contract import (
    TenderContractResourceTestMixin,
    TenderContractDocumentResourceTestMixin
)
from openprocurement.tender.limited.tests.base import (
    BaseTenderContentWebTest,
    test_lots,
    test_tender_data,
    test_tender_negotiation_data,
    test_tender_negotiation_quick_data
)
from openprocurement.tender.limited.tests.contract_blanks import (
    # TenderNegotiationQuickAccelerationTest
    create_tender_contract_negotiation_quick,
    # TenderNegotiationLot2ContractResourceTest
    sign_second_contract,
    create_two_contract,
    # TenderNegotiationLotContractResourceTest
    lot_items,
    lot_award_id_change_is_not_allowed,
    activate_contract_cancelled_lot,
    # TenderNegotiationContractResourceTest
    patch_tender_negotiation_contract,
    tender_negotiation_contract_signature_date,
    items,
    # TenderContractResourceTest
    create_tender_contract_invalid,
    create_tender_contract,
    patch_tender_contract,
    tender_contract_signature_date,
    get_tender_contract,
    get_tender_contracts,
    award_id_change_is_not_allowed,
    # TenderContractDocumentResourceTest
    not_found,
    create_tender_contract_document,
    put_tender_contract_document,
    patch_tender_contract_document,
    # TenderMergedContracts2LotsResourceTest
    not_found_contract_for_award_2,
    try_merge_not_real_award_2,
    try_merge_itself_2,
    standstill_period_2,
    activate_contract_with_complaint_2,
    cancel_award_2,
    cancel_main_award_2,
    merge_two_contracts_with_different_supliers_ids_2,
    merge_two_contracts_with_different_suppliers_scheme_2,
    set_big_value_2,
    # TenderMergedContracts3LotsResourceTest
    merge_three_contracts_3,
    standstill_period_3,
    activate_contract_with_complaint_3,
    cancel_award_3,
    cancel_main_award_3,
    try_merge_pending_award_3,
    additional_awards_dateSigned_3,
    # TenderMergedContracts4LotsResourceTest
    merge_four_contracts_4,
    sign_contract_4,
    cancel_award_4,
    cancel_main_award_4,
    cancel_first_main_award_4,
    merge_by_two_contracts_4,
    try_merge_main_contract_4,
    try_merge_contract_two_times_4,
    activate_contract_with_complaint_4,
    additional_awards_dateSigned_4,
)


class TenderContractResourceTest(BaseTenderContentWebTest, TenderContractResourceTestMixin):
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

    test_create_tender_contract_invalid = snitch(create_tender_contract_invalid)
    test_create_tender_contract = snitch(create_tender_contract)
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_tender_contract_signature_date = snitch(tender_contract_signature_date)
    test_get_tender_contract = snitch(get_tender_contract)
    test_get_tender_contracts = snitch(get_tender_contracts)
    test_award_id_change_is_not_allowed = snitch(award_id_change_is_not_allowed)


class TenderNegotiationContractResourceTest(TenderContractResourceTest):
    initial_data = test_tender_negotiation_data
    stand_still_period_days = 10

    test_patch_tender_contract = snitch(patch_tender_negotiation_contract)
    test_tender_contract_signature_date = snitch(tender_negotiation_contract_signature_date)
    test_items = snitch(items)


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

    test_items = snitch(lot_items)
    test_award_id_change_is_not_allowed = snitch(lot_award_id_change_is_not_allowed)
    test_activate_contract_cancelled_lot = snitch(activate_contract_cancelled_lot)


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

    test_sign_second_contract = snitch(sign_second_contract)
    test_create_two_contract = snitch(create_two_contract)


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
        if SANDBOX_MODE:
            response = self.app.patch_json('/tenders/{}?acc_token={}'.format(
                self.tender_id, self.tender_token), {'data': {'procurementMethodDetails': self.accelerator}})
            self.assertEqual(response.status, '200 OK')
        self.create_award()

    test_create_tender_contract_negotiation_quick = snitch(create_tender_contract_negotiation_quick)


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


class TenderContractDocumentResourceTest(BaseTenderContentWebTest, TenderContractDocumentResourceTestMixin):
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

    test_not_found = snitch(not_found)
    test_create_tender_contract_document = snitch(create_tender_contract_document)
    test_put_tender_contract_document = snitch(put_tender_contract_document)
    test_patch_tender_contract_document = snitch(patch_tender_contract_document)


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


class TenderMergedContracts2LotsResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_data = test_tender_negotiation_data
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
        self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': {'items': self.initial_data['items'] * 2}}
        )

        lots_response = list()
        for _ in range(2):
            lots_response.append(self.app.post_json(
                '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                {'data': test_lots[0]}
            ).json['data'])

        awards_response = list()

        for lot in lots_response:
            awards_response.append(self.app.post_json(
                '/tenders/{}/awards'.format(self.tender_id), {
                    'data':
                        {
                            'suppliers': [test_organization],
                            'status': 'pending',
                            'value': lot['value'],
                            'lotID': lot['id']
                        }
                }
            ).json['data'])

        self.app.authorization = authorization

        return awards_response

    def active_awards(self, *args):
        for award_id in args:
            self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
                self.tender_id, award_id, self.tender_token),
                {'data': {'status': 'active', 'qualified': True}}
            )

    test_not_found_contract_for_award = snitch(not_found_contract_for_award_2)
    test_try_merge_not_real_award = snitch(try_merge_not_real_award_2)
    test_try_merge_itself = snitch(try_merge_itself_2)
    test_standstill_period = snitch(standstill_period_2)
    test_activate_contract_with_complaint = snitch(activate_contract_with_complaint_2)
    test_cancel_award = snitch(cancel_award_2)
    test_cancel_main_award = snitch(cancel_main_award_2)
    test_merge_two_contracts_with_different_supliers_ids = snitch(merge_two_contracts_with_different_supliers_ids_2)
    test_merge_two_contracts_with_different_suppliers_scheme = snitch(
        merge_two_contracts_with_different_suppliers_scheme_2)
    test_set_big_value = snitch(set_big_value_2)


class TenderMergedContracts3LotsResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_data = test_tender_negotiation_data
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
        """Create three awards and return them"""
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))

        # Create three awards
        self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': {'items': self.initial_data['items'] * 2}}
        )

        lots_response = list()
        for _ in range(3):
            lots_response.append(self.app.post_json(
                '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                {'data': test_lots[0]}
            ).json['data'])

        awards_response = list()

        for lot in lots_response:
            awards_response.append(self.app.post_json(
                '/tenders/{}/awards'.format(self.tender_id), {
                    'data':
                        {
                            'suppliers': [test_organization],
                            'status': 'pending',
                            'value': lot['value'],
                            'lotID': lot['id']
                        }
                }
            ).json['data'])

        self.app.authorization = authorization

        return awards_response

    def active_awards(self, *args):
        for award_id in args:
            self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
                self.tender_id, award_id, self.tender_token),
                {'data': {'status': 'active', 'qualified': True}}
            )

    test_merge_three_contracts = snitch(merge_three_contracts_3)
    test_standstill_period = snitch(standstill_period_3)
    test_activate_contract_with_complaint = snitch(activate_contract_with_complaint_3)
    test_cancel_award = snitch(cancel_award_3)
    test_cancel_main_award = snitch(cancel_main_award_3)
    test_try_merge_pending_award = snitch(try_merge_pending_award_3)
    test_additional_awards_dateSigned = snitch(additional_awards_dateSigned_3)


class TenderMergedContracts4LotsResourceTest(BaseTenderContentWebTest):
    initial_status = 'active'
    initial_data = test_tender_negotiation_data
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
        """Create four awards and return them"""
        authorization = self.app.authorization
        self.app.authorization = ('Basic', ('token', ''))

        # Create four  awards
        self.app.patch_json(
            '/tenders/{}?acc_token={}'.format(self.tender_id, self.tender_token),
            {'data': {'items': self.initial_data['items'] * 2}}
        )

        lots_response = list()
        for _ in range(4):
            lots_response.append(self.app.post_json(
                '/tenders/{}/lots?acc_token={}'.format(self.tender_id, self.tender_token),
                {'data': test_lots[0]}
            ).json['data'])

        awards_response = list()

        for lot in lots_response:
            awards_response.append(self.app.post_json(
                '/tenders/{}/awards'.format(self.tender_id), {
                    'data':
                        {
                            'suppliers': [test_organization],
                            'status': 'pending',
                            'value': lot['value'],
                            'lotID': lot['id']
                        }
                }
            ).json['data'])

        self.app.authorization = authorization

        return awards_response

    def active_awards(self, *args):
        for award_id in args:
            self.app.patch_json('/tenders/{}/awards/{}?acc_token={}'.format(
                self.tender_id, award_id, self.tender_token),
                {'data': {'status': 'active', 'qualified': True}}
            )

    test_merge_four_contracts = snitch(merge_four_contracts_4)
    test_sign_contract = snitch(sign_contract_4)
    test_cancel_award = snitch(cancel_award_4)
    test_cancel_main_award = snitch(cancel_main_award_4)
    test_cancel_first_main_award = snitch(cancel_first_main_award_4)
    test_merge_by_two_contracts = snitch(merge_by_two_contracts_4)
    test_try_merge_main_contract = snitch(try_merge_main_contract_4)
    test_try_merge_contract_two_times = snitch(try_merge_contract_two_times_4)
    test_activate_contract_with_complaint = snitch(activate_contract_with_complaint_4)
    test_additional_awards_dateSigned = snitch(additional_awards_dateSigned_4)


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
