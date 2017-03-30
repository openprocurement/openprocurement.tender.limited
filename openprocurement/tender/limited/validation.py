# -*- coding: utf-8 -*-
from openprocurement.api.validation import validate_data, ViewPermissionValidationError
from openprocurement.api.utils import update_logging_context  # XXX tender context


def validate_complaint_data(request):
    if not request.check_accreditation(request.tender.edit_accreditation):
        request.errors.add('procurementMethodType', 'accreditation', 'Broker Accreditation level does not permit complaint creation')
        request.errors.status = 403
        return
    if request.tender.get('mode', None) is None and request.check_accreditation('t'):
        request.errors.add('procurementMethodType', 'mode', 'Broker Accreditation level does not permit complaint creation')
        request.errors.status = 403
        return
    update_logging_context(request, {'complaint_id': '__new__'})
    model = type(request.context).complaints.model_class
    return validate_data(request, model)


def validate_patch_complaint_data(request):
    model = type(request.context.__parent__).complaints.model_class
    return validate_data(request, model, True)

# tender
def validate_chronograph_role(request):
    if request.authenticated_role == 'chronograph':
        request.errors.add('body', 'data', 'Chronograph has no power over me!')
        request.errors.status = 403
        raise ViewPermissionValidationError


def validate_update_tender_with_awards(request, tender):
    if tender.awards:
        request.errors.add('body', 'data', 'Can\'t update tender when there is at least one award.')
        request.errors.status = 403
        raise ViewPermissionValidationError

#tender document
def validate_add_document_not_in_tender_active_status(request):
    if request.validated['tender_status'] != 'active':
        request.errors.add('body', 'data', 'Can\'t add document in current ({}) tender status'.format(request.validated['tender_status']))
        request.errors.status = 403
        raise ViewPermissionValidationError


def validate_update_document_not_in_tender_active_status(request):
    if request.validated['tender_status'] != 'active':
        request.errors.add('body', 'data', 'Can\'t update document in current ({}) tender status'.format(request.validated['tender_status']))
        request.errors.status = 403
        raise ViewPermissionValidationError
