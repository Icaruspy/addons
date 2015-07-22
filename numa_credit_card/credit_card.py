#-*- coding: utf-8 -*-
##############################################################################
#
#    NUMA Extreme Systems (www.numaes.com)
#    Copyright (C) 2013
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.osv.osv import Model, TransientModel, except_osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import tools
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

DATE_FORMAT = "%Y-%m-%d"

class res_company(Model):
    _inherit = "res.company"

    _columns = {
        'cc_receive_account': fields.many2one('account.account', 'Account for CC Vouchers', 
                                           help="Account used to register Credit Card Vouchers"),
        'cc_commission_account': fields.many2one('account.account', 'Account for CC Vouchers commissions', 
                                           help="Account used to register Credit Card Vouchers commissions"),
        'cc_reject_service': fields.many2one('product.product', 'Service for rejected credit card vouchers',
                                           help="When a credit card voucher is rejected or got back, service to put on Debit Note"),
    }

class credit_card_account(Model):
    _name = "account.credit_card_account"

    def _get_default_company(self, cr, uid, context=None):
        context = context or {}

        company_id = context.get('default_company_id')
        if not company_id:
            company_id = self.pool['res.users']._get_company(cr, uid, context=context)
        return company_id

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'ref': fields.char('CC reference', size=64),
        'company': fields.many2one('res.company', 'Company', required=True),
        'bank_account': fields.many2one('res.partner.bank', 'Issuer account', 
                                          required=True, select=True, 
                                          readonly=False),
        'receive_account': fields.many2one('account.account', 'Account', 
                                           required=True, select=True,
                                           readonly=False),                
        'state': fields.selection([
                        ('active', 'Active'),
                        ('suspended', 'Suspended'),
                        ('canceled', 'Canceled')], 'State',
                        required=True, select=True),
        'suspended_on': fields.date('Suspended on', readonly=True),
        'canceled_on': fields.date('Canceled on', readonly=True),
        'payed_after': fields.integer('Paid after [days]'),
        'commission_p': fields.float('Expenses [%]', digits=(5,2)),
    }

    _defaults = {
        'company': _get_default_company,
        'state': 'active',
        'payed_after': 15,
    }

    def onchange_company(self, cr, uid, ids, company_id, context=None):
        if company_id:
            return {'domain': {'bank_account': [('company_id','=',company_id)]}}
        else:
            return {'domain': {'bank_account': []}}

    def action_suspend(self, cr, uid, ids, context=None):
        for cca in self.browse (cr, uid, ids, context=context):
            if not cca.state in ['active']:
                raise except_osv(_("Error"), 
                                 _("You cannot suspend credit card account (%s) on current state(%s)!") % (cca.name, _(cca.state)))

            cca.write ({'state': 'suspended',
                        'suspended_on': fields.date.context_today(self, cr, uid, context=context),
                        'canceled_on': False})
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        for cca in self.browse (cr, uid, ids, context=context):
            if not cca.state in ['active', 'suspended']:
                raise except_osv(_("Error"), 
                                 _("You cannot suspend credit card account (%s) on current state(%s)!") % (cca.name, _(cca.state)))

            cca.write ({'state': 'suspended',
                        'canceled_on': fields.date.context_today(self, cr, uid, context=context)})
        return True

    def action_back_to_active(self, cr, uid, ids, context=None):
        for cca in self.browse (cr, uid, ids, context=context):
            if not cca.state in ['canceled', 'suspended']:
                raise except_osv(_("Error"), 
                                 _("You cannot reactivate credit card account (%s) on current state(%s)!") % (cca.name, _(cca.state)))

            cca.write ({'state': 'active',
                        'canceled_on': False, 'suspended_on': False})
        return True

class credit_card_voucher (Model):
    _name = "account.credit_card_voucher"

    def _get_default_company(self, cr, uid, context=None):
        context = context or {}

        company_id = context.get('default_company_id')
        if not company_id:
            company_id = self.pool['res.users']._get_company(cr, uid, context=context)
        return company_id

    def _get_default_currency(self, cr, uid, context=None):
        context = context or {}

        c_id = context.get('default_currency', False)
        if c_id:
            return c_id

        company_id = self._get_default_company(cr, uid, context=context)
        if company_id:
            company_obj = self.pool['res.company']
            company = company_obj.browse(cr, uid, company_id, context=context)
            return company.currency_id.id
        else:
            return False

    def _get_default_received_from(self, cr, uid, context=None):
        if not context: context = {}
        rf_id = context.get('default_received_from', False)
        if rf_id:
            return rf_id

        company_id = self._get_default_company(cr, uid, context=context)
        if company_id:
            company_obj = self.pool['res.company']
            company = company_obj.browse(cr, uid, company_id, context=context)
            return company.partner_id.id
        else:
            return False

    def _get_default_received_on_account(self, cr, uid, context=None):
        if not context: context = {}
        roa_id = context.get('default_received_on_account', False)
        if roa_id:
            return roa_id

        company_id = self._get_default_company(cr, uid, context=context)
        if company_id:
            company_obj = self.pool['res.company']
            company = company_obj.browse(cr, uid, company_id, context=context)
            return company.cc_receive_account and company.cc_receive_account.id or False
        else:
            return False

    _columns = {
        'name': fields.char ('Voucher number', size=32, 
                             required=True, select=True,
                             readonly=True, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft','Draft'), 
                                   ('data_complete', 'Data complete'),
                                   ('receivable','Receivable'), 
                                   ('cashed','Cashed'), 
                                   ('rejected','Rejected'), 
                                   ('canceled', 'Canceled')], 'State', readonly=True, select=True),
        'cc_account': fields.many2one('account.credit_card_account', 'Credit Card Account',
                                      required=True, select=True,
                                      readonly=True, states={'draft':[('readonly',False)]}),

        'original_amount':fields.float('Amount [currency]', 
                                       digits_compute=dp.get_precision('Account'), 
                                       required=True, 
                                       readonly=True, states={'draft':[('readonly',False)]}),
        'amount': fields.float("Amount", 
                               digits_compute=dp.get_precision('Account')),
        'currency':fields.many2one('res.currency', 'Currency', 
                                      required=True, select=True,
                                      readonly=True, states={'draft':[('readonly',False)]}),
        'received_on_account': fields.many2one('account.account', 'Received on account',
                                    select=True, 
                                    readonly=True, states={'draft':[('readonly',False)]}),

        'received_on':fields.date('Reception date', 
                                  select=True, 
                                  readonly=True, states={'draft':[('readonly',False)]}),
        'maturity_date':fields.date('Due date', 
                                    required=True, select=True, 
                                    readonly=True, states={'draft':[('readonly',False)]}),

        'received_from':fields.many2one('res.partner', 'Received from', 
                                        select=True, required=True, 
                                        readonly=True, states={'draft':[('readonly',False)]}),

        'cashed_on':fields.date('Cashed on', 
                                readonly=True, states={'draft':[('readonly',False)], 'issued':[('readonly',False)]}),

        'rejected_on':fields.date('Rejected on', 
                                readonly=True, states={'draft':[('readonly',False)], 'receivable':[('readonly',False)]}),

        'got_back_on':fields.date('Got back on', 
                                readonly=True, states={'draft':[('readonly',False)], 'receivable':[('readonly',False)]}),

        'company': fields.many2one('res.company', 'Company'),
    }
    
    _defaults = {
        'state' : 'draft',
        'received_on' : fields.date.context_today,
        'maturity_date': fields.date.context_today,
        'company': _get_default_company,
        'currency': _get_default_currency,
        'received_from': _get_default_received_from,
        'received_on_account': _get_default_received_on_account,
    }

    def onchange_original_amount (self, cr, uid, ids, original_amount, currency_id, company_id, context=None):
        context = context or {}

        currency_obj = self.pool['res.currency']
        company_obj = self.pool['res.company']

        res = {}

        if company_id:
            company = company_obj.browse(cr, uid, company_id, context=None)

            res['amount'] = currency_obj.compute (cr, uid, currency_id, company.currency_id.id, original_amount, context=context)

        return {'value': res}
        
    def onchange_company(self, cr, uid, ids, company_id, transferable, context=None):        
        if company_id:
            res = {}

            company_obj = self.pool['res.company']
            company = company_obj.browse(cr, uid, company_id, context=context)
            res['received_on'] = company.cc_receive_account and company.cc_receive_account.id or False
            return {'value': res}
        else:
            return False

    def complete(self, cr, uid, ids, context=None):
        for ccv in self.browse (cr, uid, ids, context=context):
            if not ccv.state in ('draft'):
                raise except_osv(_("Error"), 
                                 _("You cannot complete the document (%s) on current state (%s)!") % (ccv.name, _(ccv.state)))
            ccv.write({'state': 'data_complete'})

        return True     

    def back_to_draft(self, cr, uid, ids, context=None):
        for doc in self.browse (cr, uid, ids, context=context):
            if not doc.state in ('data_complete'):
                raise except_osv(_("Error"), 
                                 _("You cannot change back to draft the document (%s) on current state (%s)!") % (ccv.name, _(ccv.state)))
            ccv.write({'state': 'draft'})

        return True     

    def receive(self, cr, uid, ids, received_date=None, context=None):
        for ccv in self.browse (cr, uid, ids, context=context):
            if ccv.state not in ['data_complete','draft']:
                raise except_osv(_("Error"), 
                                 _("Only documents on data complete state could be confirmed (%s)!") % ccv.name)

            if not (ccv.received_from) or not (ccv.currency and ccv.maturity_date):
                raise except_osv(_("Error"), 
                                 _("Incomplete data. Received from, currency are mandatory!"))

            effective_date = received_date or \
                             ccv.received_on or \
                             fields.date.context_today(self, cr, uid, context=context)

            dt_today = datetime.strptime(fields.date.context_today(self, cr, uid, context=context), DATE_FORMAT)
            dt_maturity_date = dt_today + timedelta(days=ccv.cc_account.payed_after)

            maturity_date = ccv.maturity_date or dt_maturity_date.strftime(DATE_FORMAT)

            ccv.write ({'received_on': effective_date, 
                        'maturity_date': maturity_date,
                        'cashed_on': False,
                        'rejected_on': False,
                        'state': 'receivable'})                    
        return True

    def reject(self, cr, uid, ids, rejected_date=None, context=None):
        effective_date = rejected_date or fields.date.context_today(self, cr, uid, context=context)

        for ccv in self.browse (cr, uid, ids, context=context):
            if not ccv.state in ('receivable', 'cashed'):
                raise except_osv(_("Error"), 
                                 _("You cannot reject the credit card voucher (%s) on current state (%s)!") % (ccv.name, _(ccv.state)))

            ccv.write({'rejected_on': effective_date,
                       'state': 'rejected'})

        return True     

    def get_back(self, cr, uid, ids, gb_date=None, context=None):
        effective_date = gb_date or fields.date.context_today(self, cr, uid, context=context)

        for ccv in self.browse (cr, uid, ids, context=context):
            if not ccv.state in ('receivable', 'cashed'):
                raise except_osv(_("Error"), 
                                 _("You cannot get back the credit card voucher (%s) on current state (%s)!") % (ccv.name, _(ccv.state)))

            ccv.write({'got_back_on': effective_date,
                       'state': 'canceled'})

        return True     

    def cash(self, cr, uid, ids, cashed_date=None, context=None):
        effective_date = cashed_date or fields.date.context_today(self, cr, uid, context=context)

        for ccv in self.browse (cr, uid, ids, context=context):
            if not ccv.state in ('receivable', 'rejected', 'third_party'):
                raise except_osv(_("Error"), 
                                 _("You cannot cash the credit card voucher (%s) on current state (%s)!") % (ccv.name, _(ccv.state)))

            ccv.write({'cashed_on': effective_date, 
                       'state': 'cashed'})

        return True

    def action_complete(self, cr, uid, ids, context=None):
        self.complete(cr, uid, ids, context=context)
        return True

    def action_back_to_draft(self, cr, uid, ids, context=None):
        self.back_to_draft(cr, uid, ids, context=context)
        return True

    def action_confirm(self, cr, uid, ids, context=None):
        for ccv in self.browse(cr, uid, ids, context=context):
            if ccv.state != 'draft':
                raise except_osv(_("Error"), 
                                 _("You cannot confirm the credit card voucher (%s) on current state(%s)!") % (ccv.name, _(ccv.state)))

        return {
            'name':_("Receive credit card vouchers"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.receive_ccv',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

    def action_cash(self, cr, uid, ids, context=None):
        for ccv in self.browse(cr, uid, ids, context=context):
            if ccv.state != 'receivable':
                raise except_osv(_("Error"), 
                                 _("You cannot cash the credit card voucher (%s) on current state(%s)!") % (ccv.name, _(ccv.state)))

        return {
            'name':_("Cash Credit Card Vouchers"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.cash_ccv',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

    def action_reject(self, cr, uid, ids, context=None):
        for ccv in self.browse(cr, uid, ids, context=context):
            if ccv.state != 'receivable':
                raise except_osv(_("Error"), 
                                 _("You cannot reject the credit card voucher (%s) on current state(%s)!") % (ccv.name, _(ccv.state)))

        return {
            'name':_("Reject Credit Card Vouchers"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.reject_ccv',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

    def action_get_back(self, cr, uid, ids, context=None):
        for ccv in self.browse(cr, uid, ids, context=context):
            if ccv.state != 'receivable':
                raise except_osv(_("Error"), 
                                 _("You cannot get back credit card voucher (%s) on current state(%s)!") % (ccv.name, _(ccv.state)))

        return {
            'name':_("Get back Credit Card Vouchers"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.get_back_ccv',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

class receive_ccv (TransientModel):
    _name = 'account.receive_ccv'

    def _get_default_journal(self, cr, uid, context=None):
        if context is None: context = {}
        j_id = context.get('journal_id', False)
        if not j_id:
            journal_obj = self.pool['account.journal']
            j_ids = journal_obj.search(cr, uid, [('type','=','sale')], context=context)
            if j_ids and len(j_ids)==1:
                j_id = j_ids[0]
        return j_id

    def _get_ccvs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        ccv_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = ccv_ids
        return res

    _columns = {
        'ccvs': fields.function(_get_ccvs, method=True, 
                                type="one2many", relation="account.credit_card_voucher"),
        'journal': fields.many2one('account.journal', 'Journal', required=True),
        'receive_date':fields.date('Reception date', required=True),
        'period': fields.many2one('account.period', 'Period', required=True),
    }

    _defaults = {
        'receive_date': fields.date.context_today,
        'journal': _get_default_journal,
    }

    def onchange_receive_date(self, cr, uid, ids, receive_date, journal_id, context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if not receive_date:
            return False

        if not context: context = {}

        period_pool = self.pool['account.period']
        journal_pool = self.pool['account.journal']

        res = {'value': {}}

        if journal_id:
            journal = journal_pool.browse (cr, uid, journal_id)
            pids = period_pool.search(cr, uid, [('date_start', '<=', receive_date), ('date_stop', '>=', receive_date), ('company_id', '=', journal.company_id.id)])
        else:
            pids = period_pool.search(cr, uid, [('date_start', '<=', receive_date), ('date_stop', '>=', receive_date)])
        if pids:
            if not 'value' in res:
                res['value'] = {}
            res['value']['period'] = pids[0]

        return res

    def onchange_journal (self, cr, uid, ids, journal_id, receive_date, context=None):
        if not journal_id:
            return False

        journal_obj = self.pool['account.journal']
        period_obj = self.pool['account.period']

        journal = journal_obj.browse(cr, uid, journal_id, context=context)
        res = {'receive_account': journal.default_debit_account_id and journal.default_debit_account_id.id or False}

        ocrd = self.onchange_receive_date (cr, uid, ids, receive_date, journal_id, context=context)
        if ocrd and 'value' in ocrd:
            res.update(ocrd['value'])

        return {'value': res}

    def action_receive(self, cr, uid, ids, context=None):
        if not context: context = {}

        move_obj = self.pool['account.move']
        move_line_obj = self.pool['account.move.line']
        currency_obj = self.pool['res.currency']
        holiday_obj = self.pool.get('account.holiday')

        for rd in self.browse (cr, uid, ids, context=context):

            move_vals = {
                'name': '/',
                'journal_id': rd.journal.id,
                'narration': _("Received"),
                'date': rd.receive_date,
                'ref': rd.journal.name,
                'period_id': rd.period.id,
            }
            move_id = move_obj.create(cr, uid, move_vals, context=context)

            company_currency_id = rd.journal.company_id.currency_id.id

            #Generate a pair of movement for each credit card voucher, 
            #one for the debit account of the journal and one for the credit account (by default, the credit account of the journal)

            for ccv in rd.ccvs:
                amount_to_receive = currency_obj.compute(cr, uid, ccv.currency.id, company_currency_id, ccv.original_amount, context=context)

                # Compute maturity taking into account laborable days and holidays
                
                maturity_date = holiday_obj.add_delta_to_date(cr, uid, 
                                    ccv.company.fiscal_country.id, 
                                    ccv.maturity_date, 
                                    ccv.cc_account.payed_after,
                                    context=context)

                move_line = {
                    'name': ccv.name,
                    'journal_id': rd.journal.id,
                    'period_id': rd.period.id,
                    'account_id': ccv.cc_account.receive_account.id,
                    'move_id': move_id,
                    'partner_id': ccv.received_from.id,
                    'currency_id': company_currency_id != ccv.currency.id and ccv.currency.id or False,
                    'amount_currency': company_currency_id != ccv.currency.id and ccv.original_amount or 0.0,
                    'analytic_account_id': False,
                    'quantity': 1,
                    'debit': ccv.amount,
                    'credit': 0.0,
                    'date_maturity': rd.receive_date,
                }

                receipt_line = move_line_obj.create(cr, uid, move_line, context=context)

                move_line.update({
                    'account_id': ccv.received_from.property_account_receivable.id,
                    'amount_currency': -move_line['amount_currency'],
                    'credit': ccv.amount,
                    'debit': 0.0,
                })

                cashed_move_line_id = move_line_obj.create(cr, uid, move_line, context=context)

                ccv.write({'received_on_account': ccv.cc_account.receive_account.id})
                ccv.receive(rd.receive_date)

            move_obj.post(cr, uid, [move_id], context={})

        return {'type': 'ir.actions.act_window_close'}

class cash_ccv (TransientModel):
    _name = 'account.cash_ccv'

    def _get_default_journal(self, cr, uid, context=None):
        if context is None: context = {}
        j_id = context.get('journal_id', False)
        if not j_id:
            journal_obj = self.pool['account.journal']
            j_ids = journal_obj.search(cr, uid, [('type','=','sale')], context=context)
            if j_ids and len(j_ids)==1:
                j_id = j_ids[0]
        return j_id
        
    def _get_ccvs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        ccv_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = ccv_ids
        return res

    _columns = {
        'ccvs': fields.function(_get_ccvs, method=True, 
                                type="one2many", relation="account.credit_card_voucher"),
        'journal': fields.many2one('account.journal', 'Journal', required=True),
        'cash_date':fields.date('Cash date', required=True),
        'period': fields.many2one('account.period', 'Period', required=True),
        'cash_account': fields.many2one('account.account', 'Cash account', required=True)
    }

    _defaults = {
        'cash_date': fields.date.context_today,
        'journal': _get_default_journal,
    }

    def onchange_cash_date(self, cr, uid, ids, cash_date, journal_id, context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if not cash_date:
            return False

        if not context: context = {}

        period_pool = self.pool['account.period']
        journal_pool = self.pool['account.journal']

        res = {'value':{}}

        if journal_id:
            journal = journal_pool.browse (cr, uid, journal_id)
            pids = period_pool.search(cr, uid, [('date_start', '<=', cash_date), ('date_stop', '>=', cash_date), ('company_id', '=', journal.company_id.id)])
        else:
            pids = period_pool.search(cr, uid, [('date_start', '<=', cash_date), ('date_stop', '>=', cash_date)])
        if pids:
            if not 'value' in res:
                res['value'] = {}
            res['value']['period'] = pids[0]

        return res

    def onchange_journal (self, cr, uid, ids, journal_id, cash_date, context=None):
        if not journal_id:
            return False

        journal_obj = self.pool['account.journal']
        period_obj = self.pool['account.period']

        journal = journal_obj.browse(cr, uid, journal_id, context=context)
        res = {'cash_account': journal.default_debit_account_id and journal.default_debit_account_id.id or False}

        occd = self.onchange_cash_date (cr, uid, ids, cash_date, journal_id, context=context)
        if occd and 'value' in occd:
            res.update(occd['value'])

        return {'value': res}

    def action_cash(self, cr, uid, ids, context=None):
        if not context: context = {}

        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        for cd in self.browse (cr, uid, ids, context=context):

            move_vals = {
                'name': '/',
                'journal_id': cd.journal.id,
                'narration': _("Cashed"),
                'date': cd.cash_date,
                'ref': cd.journal.name,
                'period_id': cd.period.id,
            }
            move_id = move_obj.create(cr, uid, move_vals, context=context)

            company_currency_id = cd.journal.company_id.currency_id.id

            #Generate a pair of movements for each credit card voucher, 
            #one for the debit account of the journal and one for the credit account (by default, the credit account of the journal)

            for ccv in cd.ccvs:
                amount_to_receive = currency_obj.compute(cr, uid, ccv.currency.id, company_currency_id, ccv.original_amount, context=context)

                commission = ccv.amount * (ccv.cc_account.commission_p / 100.0)
                amount_to_cash = ccv.amount - commission

                move_line = {
                    'name': ccv.name,
                    'journal_id': cd.journal.id,
                    'period_id': cd.period.id,
                    'account_id': cd.cash_account.id,
                    'move_id': move_id,
                    'partner_id': ccv.received_from.id,
                    'currency_id': company_currency_id != ccv.currency.id and ccv.currency.id or False,
                    'amount_currency': company_currency_id != ccv.currency.id and ccv.original_amount * (amount_to_cash/ccv.amount) or 0.0,
                    'analytic_account_id': False,
                    'quantity': 1,
                    'debit': amount_to_cash,
                    'credit': 0.0,
                    'date_maturity': cd.cash_date,
                }

                receipt_line = move_line_obj.create(cr, uid, move_line, context=context)

                if commission > 0.0:
                    move_line.update({
                        'amount_currency': company_currency_id != ccv.currency.id and ccv.original_amount * (commission/ccv.amount) or 0.0,
                        'account_id': ccv.received_on_account.id,
                        'debit': commission,
                        'credit': 0.0,
                    })

                    commission_move_line_id = move_line_obj.create(cr, uid, move_line, context=context)

                move_line.update({
                    'amount_currency': company_currency_id != ccv.currency.id and -ccv.original_amount or 0.0,
                    'account_id': ccv.received_on_account.id,
                    'debit': 0.0,
                    'credit': ccv.amount,
                })

                cashed_move_line_id = move_line_obj.create(cr, uid, move_line, context=context)

                ccv.cash(cd.cash_date)

            move_obj.post(cr, uid, [move_id], context={})

        return {'type': 'ir.actions.act_window_close'}

class reject_ccv (TransientModel):
    _name = 'account.reject_ccv'

    def _get_ccvs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        ccv_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = ccv_ids
        return res

    _columns = {
        'ccvs': fields.function(_get_ccvs, method=True, 
                                type="one2many", relation="account.credit_card_voucher"),
    }

    def action_reject(self, cr, uid, ids, context=None):
        if not context: context = {}

        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        created_debit_notes = []

        for rd in self.browse (cr, uid, ids, context=context):

            invoice_obj = self.pool['account.invoice']
            invoice_line_obj = self.pool['account.invoice.line']

            for ccv in rd.ccvs:
                vals = invoice_obj.default_get(cr, uid, [], context=context)
                vals['partner_id'] = ccv.received_from.id
                vals['type'] = 'out_invoice'
                ocp = invoice_obj.onchange_partner_id(cr, uid, [], 
                                                      vals['type'],
                                                      vals['partner_id'])
                if ocp and 'value' in ocp:
                    vals.update(ocp['value'])

                vals['debit_note'] = True

                invoice_id = invoice_obj.create(cr, uid, vals, context=context)

                vals = invoice_line_obj.default_get(cr, uid, [], context=context)
                vals['invoice_id'] = invoice_id
                if not ccv.company.doc_reject_service:
                    raise except_osv(_("Error"), 
                                     _("No default service for rejected documents defined for company [%s]!. Please check it") % ccv.company.name)
                vals['product_id'] = ccv.company.doc_reject_service.id
                vals['quantity'] = 1
                vals['price_unit'] = ccv.amount
                vals['price_subtotal'] = ccv.amount
                vals['account_id'] = ccv.received_on_account.id
                vals['name'] = _('Reject CCV %s') % ccv.name_get()[0][1]
                invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)

                created_debit_notes.append(invoice_id)
                ccv.reject(False)

        if created_debit_notes:
            models_data = self.pool.get('ir.model.data')

            # Get lead views
            dummy, form_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_form')
            dummy, tree_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
            dummy, search_view = models_data.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')

            return {
                'name':_("Rejection debit notes"),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'context': {'default_type':'out_invoice', 'type':'out_invoice', 'journal_type': 'sale'},
                'search_view_id': search_view,
                'domain': [('id','in',created_debit_notes)],
                'views': [(tree_view or False, 'tree'), (form_view or False, 'form')],
            }
        else:            
            return {'type': 'ir.actions.act_window_close'}

class get_back_ccv (TransientModel):
    _name = 'account.get_back_ccv'

    def _get_ccvs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        ccv_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = ccv_ids
        return res

    _columns = {
        'ccvs': fields.function(_get_ccvs, method=True, 
                                type="one2many", relation="account.credit_card_voucher"),
    }

    def action_gb(self, cr, uid, ids, context=None):
        if not context: context = {}

        move_obj = self.pool['account.move']
        move_line_obj = self.pool['account.move.line']
        currency_obj = self.pool['res.currency']

        created_debit_notes = []

        for gbd in self.browse (cr, uid, ids, context=context):

            invoice_obj = self.pool['account.invoice']
            invoice_line_obj = self.pool['account.invoice.line']

            for ccv in gbd.ccvs:
                vals = invoice_obj.default_get(cr, uid, [], context=context)
                vals['partner_id'] = ccv.received_from.id
                vals['type'] = 'out_invoice'
                ocp = invoice_obj.onchange_partner_id(cr, uid, [], 
                                                      vals['type'],
                                                      vals['partner_id'])
                if ocp and 'value' in ocp:
                    vals.update(ocp['value'])

                vals['debit_note'] = True

                invoice_id = invoice_obj.create(cr, uid, vals, context=context)

                vals = invoice_line_obj.default_get(cr, uid, [], context=context)
                vals['invoice_id'] = invoice_id
                if not ccv.company.doc_reject_service:
                    raise except_osv(_("Error"), 
                                     _("No default service for rejected documents defined for company [%s]!. Please check it") % ccv.company.name)
                vals['product_id'] = ccv.company.doc_reject_service.id
                vals['quantity'] = 1
                vals['price_unit'] = ccv.amount
                vals['price_subtotal'] = ccv.amount
                vals['account_id'] = ccv.received_on_account.id
                vals['name'] = _('Get back CCV %s') % ccv.name_get()[0][1]
                invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)

                created_debit_notes.append(invoice_id)
                ccv.get_back(False)

        if created_debit_notes:
            models_data = self.pool['ir.model.data']

            # Get lead views
            dummy, form_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_form')
            dummy, tree_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
            dummy, search_view = models_data.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')

            return {
                'name':_("Getting back debit notes"),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'context': {'default_type':'out_invoice', 'type':'out_invoice', 'journal_type': 'sale'},
                'search_view_id': search_view,
                'domain': [('id','in',created_debit_notes)],
                'views': [(tree_view or False, 'tree'), (form_view or False, 'form')],
            }
        else:            
            return {'type': 'ir.actions.act_window_close'}


