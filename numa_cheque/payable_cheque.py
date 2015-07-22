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
import openerp.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


class res_company(Model):
    _inherit = "res.company"

    _columns = {
        'nt_pdocs_account': fields.many2one('account.account', 'Account for NT payable docs', 
                                           domain=[('type','!=','view')],
                                           help="Account used to register non transferable payable documents"),
        't_pdocs_account': fields.many2one('account.account', 'Account for payable docs', 
                                           domain=[('type','!=','view')],
                                           help="Account used to register transferable payable documents"),
        'pdoc_reject_service': fields.many2one('product.product', 'Service for rejected payable docs',
                                              domain=[('type','=','service')],
                                              help="When a payable document is rejected or got back, service to put on Debit Note"),
        'pdoc_reject_charge_service': fields.many2one('product.product', 'Service for rejected payable docs expenses',
                                              domain=[('type','=','service')],
                                              help="When a payable document is rejected or got back, service to add to Debit Note in order to charge processing and other expenses (optional)"),
    }


class payable_document (Model):
    _name = "account.payable_document"

    def _get_default_company(self, cr, uid, context=None):
        context = context or {}

        company_id = context.get('default_company')
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

    def _get_default_payed_to(self, cr, uid, context=None):
        if not context: context = {}
        rf_id = context.get('default_payed_to', False)
        if rf_id:
            return rf_id

        company_id = self._get_default_company(cr, uid, context=context)
        if company_id:
            company_obj = self.pool['res.company']
            company = company_obj.browse(cr, uid, company_id, context=context)
            return company.partner_id.id
        else:
            return False

    def _get_default_payed_on_account(self, cr, uid, context=None):
        if not context: context = {}
        roa_id = context.get('default_payed_on_account', False)
        if roa_id:
            return roa_id

        company_id = self._get_default_company(cr, uid, context=context)
        if company_id:
            company_obj = self.pool['res.company']
            company = company_obj.browse(cr, uid, company_id, context=context)
            return company.t_docs_account and company.t_docs_account.id or False
        else:
            return False

    _columns = {
        'name': fields.char ('Cheque or document number', size=32, 
                             required=True, select=True,
                             readonly=True, states={'draft':[('readonly',False)]}),
        'number': fields.integer('Internal number', readonly=True),
        'state': fields.selection([('draft','Draft'),
                                   ('data_complete','Data complete'), 
                                   ('payable','Payable'), 
                                   ('cashed','Cashed'), 
                                   ('rejected','Rejected'), 
                                   ('canceled', 'Canceled')], 'State', readonly=True, select=True),
        'doc_type': fields.selection([('cheque', 'Cheque'), 
                                      ('other', 'Other document type')], 
                                      'Document type', 
                                      required=True, select=True, 
                                      readonly=True, states={'draft':[('readonly',False)]}),
        'issuer_account': fields.many2one('res.partner.bank', 'Issuer account', 
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
        'issued_date':fields.date('Issued date', 
                                    required=True, select=True, 
                                    readonly=True, states={'draft':[('readonly',False)]}),
        'maturity_date':fields.date('Due date', 
                                    required=True, select=True, 
                                    readonly=True, states={'draft':[('readonly',False)]}),

        'payed_on_account': fields.many2one('account.account', 'Payed on account',
                                    select=True, 
                                    readonly=True, states={'draft':[('readonly',False)]}),

        'transferable':fields.boolean('Transferable?', 
                                      help='Document could be handed to a third party?'),
        'validity_after_maturity': fields.integer('Validity after due date [days]', 
                                                  help='Number of days after due date the document is still valid', 
                                                  readony=True, states={'draft':[('readonly',False)]}),

        'payed_on':fields.date('Payment date', 
                                  select=True, 
                                  readonly=True, states={'draft':[('readonly',False)]}),
        'payed_to':fields.many2one('res.partner', 'Payed to', 
                                        select=True, required=True, 
                                        readonly=True, states={'draft':[('readonly',False)]}),

        'cashed_on':fields.date('Cashed on', 
                                readonly=True, states={'draft':[('readonly',False)], 'issued':[('readonly',False)]}),

        'rejected_on':fields.date('Rejected on', 
                                readonly=True, states={'draft':[('readonly',False)], 'payable':[('readonly',False)]}),

        'back_from_partner_on':fields.date('Back from partner on', 
                                readonly=True, states={'draft':[('readonly',False)], 'payable':[('readonly',False)]}),

        'company': fields.many2one('res.company', 'Company'),
        'company_partner': fields.related('company','partner_id',
                                          string="Company partner",
                                          type="many2one", relation="res.partner",
                                          readonly="True")
    }
    
    _defaults = {
        'state' : 'draft',
        'doc_type' : 'cheque',
        'payed_on' : fields.date.context_today,
        'issued_date': fields.date.context_today,
        'maturity_date': fields.date.context_today,
        'validity_after_maturity': 30,
        'company': _get_default_company,
        'currency': _get_default_currency,
        'payed_to': _get_default_payed_to,
        'transferable': True,
        'payed_on_account': _get_default_payed_on_account,
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
        
    def onchange_transferable(self, cr, uid, ids, transferable, company_id, context=None):
        context = context or {}

        company_obj = self.pool['res.company']

        res = {}

        if company_id:
            company = company_obj.browse(cr, uid, company_id, context=None)
            res['payed_on_account'] = transferable and (company.t_pdocs_account and company.t_pdocs_account.id or False) or \
                                                       (company.nt_pdocs_account and company.nt_pdocs_account.id or False),

        return {'value': res}

    def onchange_company(self, cr, uid, ids, company_id, transferable, context=None):
        company_obj = self.pool['res.company']
        if company_id:
            res = {}
            company = company_obj.browse(cr, uid, company_id, context=context)
            res['company_partner'] = company.partner_id.id
            oct = self.onchange_transferable(cr, uid, ids, transferable, company_id, context=context)
            if oct and 'value' in oct:
                res.update(oct['value'])
            return {'value': res}
        else:
            return False

    def pay(self, cr, uid, ids, supplier_id, account_id, payment_date=None, context=None):
        for doc in self.browse (cr, uid, ids, context=context):
            if doc.state != 'data_complete':
                raise except_osv(_("Error"), 
                                 _("Only documents on data complete state could be confirmed (%s)!") % doc.name)

            if not (doc.doc_type == 'cheque' and doc.issuer_account and doc.name) or \
               not supplier_id or \
               not account_id or \
               not doc.payed_on or not doc.payed_to or \
               not (doc.currency and doc.maturity_date) or \
               doc.original_amount <= 0.0:
                raise except_osv(_("Error"), 
                                 _("Incomplete data. Payed to, currency, payment date and if cheque, issuer account and cheque number are mandatory!"))

            effective_date = payment_date or \
                             doc.payed_on or \
                             fields.date.context_today(self, cr, uid, context=context)

            maturity_date = doc.maturity_date or fields.date.context_today(self, cr, uid, context=context)

            doc.write ({'payed_to': supplier_id,
                        'payed_on_account': account_id,
                        'payed_on': effective_date, 
                        'maturity_date': maturity_date,
                        'cashed_on': False,
                        'rejected_on': False,
                        'state': 'payable'})                    
        return True

    def complete(self, cr, uid, ids, context=None):
        for doc in self.browse (cr, uid, ids, context=context):
            if not doc.state in ('draft'):
                raise except_osv(_("Error"), 
                                 _("You cannot complete the payable document (%s) on current state (%s)!") % (doc.name, _(doc.state)))
            doc.write({'state': 'data_complete'})

        return True     

    def back_to_draft(self, cr, uid, ids, context=None):
        for doc in self.browse (cr, uid, ids, context=context):
            if not doc.state in ('data_complete'):
                raise except_osv(_("Error"), 
                                 _("You cannot change back to draft the payable document (%s) on current state (%s)!") % (doc.name, _(doc.state)))
            doc.write({'state': 'draft'})

        return True     

    def reject(self, cr, uid, ids, rejected_date=None, context=None):
        effective_date = rejected_date or fields.date.context_today(self, cr, uid, context=context)

        for doc in self.browse (cr, uid, ids, context=context):
            if not doc.state in ('payable', 'cashed'):
                raise except_osv(_("Error"), 
                                 _("You cannot reject the payable document (%s) on current state (%s)!") % (doc.name, _(doc.state)))

            doc.write({'rejected_on': effective_date,
                       'state': 'rejected'})

        return True     

    def cash(self, cr, uid, ids, cashed_date=None, context=None):
        effective_date = cashed_date or fields.date.context_today(self, cr, uid, context=context)

        for doc in self.browse (cr, uid, ids, context=context):
            if not doc.state in ('payable', 'rejected'):
                raise except_osv(_("Error"), 
                                 _("You cannot cash the payable document (%s) on current state (%s)!") % (doc.name, _(doc.state)))

            doc.write({'cashed_on': effective_date, 
                       'state': 'cashed'})

        return True

    def get_back (self, cr, uid, ids, handed_out_on=None, context=None):
        effective_date = handed_out_on or fields.date.context_today(self, cr, uid, context=context)

        for doc in self.browse (cr, uid, ids, context=context):
            if not doc.state in ('payable'):
                raise except_osv(_("Error"), 
                                 _("You cannot get back the payable document (%s) on current state(%s)!") % (doc.name, _(doc.state)))

            doc.write ({'back_from_partner_on': effective_date,
                        'state': 'canceled'})                    
        return True

    def action_complete(self, cr, uid, ids, context=None):
        self.complete(cr, uid, ids, context=context)
        return True

    def action_back_to_draft(self, cr, uid, ids, context=None):
        self.back_to_draft(cr, uid, ids, context=context)
        return True

    def action_confirm(self, cr, uid, ids, context=None):
        assert ids or len(ids) == 1, 'One at the time'

        doc = self.browse(cr, uid, ids[0], context=context)

        if doc.state != 'data_complete':
            raise except_osv(_("Error"), 
                             _("You cannot confirm the payable document (%s) on current state(%s)!") % (doc.name, _(doc.state)))

        return {
            'name':_("Pay payable document %s") % doc.name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.pay_pdocument',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': context or {},
        }

    def action_cash(self, cr, uid, ids, context=None):
        assert ids or len(ids) == 1, 'One at the time'

        doc = self.browse(cr, uid, ids[0], context=context)

        if doc.state != 'payable':
            raise except_osv(_("Error"), 
                             _("You cannot cash the payable document (%s) on current state(%s)!") % (doc.name, _(doc.state)))

        return {
            'name':_("Cash payable document %s") % doc.name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.cash_pdocument',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

    def action_reject(self, cr, uid, ids, context=None):
        assert ids or len(ids) == 1, 'One at the time'

        doc = self.browse(cr, uid, ids[0], context=context)

        if doc.state != 'payable':
            raise except_osv(_("Error"), 
                             _("You cannot reject the payable document (%s) on current state(%s)!") % (doc.name, _(doc.state)))

        return {
            'name':_("Reject payable document %s") % doc.name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.reject_pdocument',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

    def action_get_back(self, cr, uid, ids, context=None):
        assert ids or len(ids) == 1, 'One at the time'

        doc = self.browse(cr, uid, ids[0], context=context)

        if doc.state != 'payable':
            raise except_osv(_("Error"), 
                             _("You cannot get back payable document (%s) on current state(%s)!") % (doc.name, _(doc.state)))

        return {
            'name':_("Get back payable document %s") % doc.name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.get_back_pdocument',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context or {},
        }

class pay_pdocument (TransientModel):
    _name = 'account.pay_pdocument'

    def _get_default_journal(self, cr, uid, context=None):
        if context is None: context = {}
        j_id = context.get('journal_id', False)
        if not j_id:
            journal_obj = self.pool['account.journal']
            j_ids = journal_obj.search(cr, uid, [('type','=','purchase')], context=context)
            if j_ids and len(j_ids)==1:
                j_id = j_ids[0]
        return j_id
        
    def _get_doc(self, cr, uid, context=None):
        context = context or {}

        doc_id = context.get('active_id')
        return doc_id

    _columns = {
        'doc': fields.many2one("account.payable_document", 'Document'),
        'company': fields.many2one('res.company', 'Company'),
        'supplier': fields.many2one('res.partner', 'Supplier', required=True),
        'journal': fields.many2one('account.journal', 'Journal', required=True),
        'payment_date':fields.date('Payment date', required=True),
        'period': fields.many2one('account.period', 'Period', required=True),
        'payment_account': fields.many2one('account.account', 'Payment account', required=True)
    }

    _defaults = {
        'payment_date': fields.date.context_today,
        'doc': _get_doc,
    }

    def onchange_doc(self, cr, uid, ids, doc_id, context=None):
        if doc_id:
            apd_obj = self.pool['account.payable_document']
            res = {}
            doc = apd_obj.browse(cr, uid, doc_id, context=context)
            res['company'] = doc.company.id
            return {'value': res}
        else:
            return False
            
    def onchange_supplier(self, cr, uid, ids, supplier_id, context=None):
        if supplier_id:
            partner_obj = self.pool['res.partner']
            supplier = partner_obj.browse(cr, uid, supplier_id, context=context)
            res = {}
            res['payment_account'] = supplier.property_account_payable.id
            return {'value': res}
        else:
            return False

    def onchange_company(self, cr, uid, ids, company_id, payment_date, context=None):
        company_obj = self.pool['res.company']
        if company_id:
            company = company_obj.browse(cr, uid, company_id, context=context)
            
            domain = {}
    
            domain['journal'] = [('company_id','=',company.id),('type','=','purchase')]
            domain['period'] = [('fiscalyear_id.company_id','=',company.id)]
            domain['payment_account'] = [('company_id','=',company.id),('type','!=','view')]
            
            ocpd = self.onchange_payment_date(cr, uid ,ids, payment_date, company_id, context=context)
            ocpd = ocpd or {}
            ocpd.update({'domain': domain})
            return ocpd
        else:
            return False
        
    def onchange_payment_date(self, cr, uid, ids, payment_date, company_id, context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if not payment_date or not company_id:
            return False

        if not context: context = {}

        period_pool = self.pool.get('account.period')

        res = {'value': {}}

        pids = period_pool.search(cr, uid, [('date_start', '<=', payment_date), ('date_stop', '>=', payment_date), ('company_id', '=', company_id)])
        if pids:
            if not 'value' in res:
                res['value'] = {}
            res['value']['period'] = pids[0]

        return res

    def onchange_journal (self, cr, uid, ids, journal_id, payment_date, context=None):
        if not journal_id:
            return False

        journal_obj = self.pool.get('account.journal')

        journal = journal_obj.browse(cr, uid, journal_id, context=context)
        res = {'payment_account': journal.default_credit_account_id and journal.default_credit_account_id.id or False}

        ocrd = self.onchange_payment_date (cr, uid, ids, payment_date, journal.company_id.id, context=context)
        if ocrd and 'value' in ocrd:
            res.update(ocrd['value'])

        return {'value': res}

    def action_pay_pdoc(self, cr, uid, ids, context=None):
        if not context: context = {}

        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        holiday_obj = self.pool.get('account.holiday')

        for pd in self.browse (cr, uid, ids, context=context):

            move_vals = {
                'name': '/',
                'journal_id': pd.journal.id,
                'narration': _("Pay payable document"),
                'date': pd.payment_date,
                'ref': pd.journal.name,
                'period_id': pd.period.id,
            }
            move_id = move_obj.create(cr, uid, move_vals, context=context)

            company_currency_id = pd.journal.company_id.currency_id.id

            #Generate a pair of movements for each document, 
            #one for the debit account of the journal and one for the credit account (by default, the credit account of the journal)

            doc = pd.doc
            # Compute maturity taking into account laborable days and holidays

            maturity_date = holiday_obj.add_delta_to_date(cr, uid, 
                                doc.company.fiscal_country.id, 
                                doc.maturity_date, 
                                {'immediate': 0,
                                 '24': 1,
                                 '48': 2,
                                 '72': 3,
                                 '96': 4,}.get(doc.issuer_account.bank.clearing, 0),
                                context=context)

            move_line = {
                'name': doc.name,
                'journal_id': pd.journal.id,
                'period_id': pd.period.id,
                'account_id': pd.payment_account.id,
                'move_id': move_id,
                'partner_id': doc.payed_to.id,
                'currency_id': company_currency_id != doc.currency.id and doc.currency.id or False,
                'amount_currency': company_currency_id != doc.currency.id and doc.original_amount or 0.0,
                'analytic_account_id': False,
                'quantity': 1,
                'debit': 0.0,
                'credit': doc.amount,
                'date_maturity': maturity_date,
            }

            move_line_obj.create(cr, uid, move_line, context=context)

            move_line.update({
                'account_id': doc.payed_to.property_account_receivable.id,
                'amount_currency': -move_line['amount_currency'],
                'debit': doc.amount,
                'credit': 0.0,
            })

            move_line_obj.create(cr, uid, move_line, context=context)

            doc.pay(pd.supplier.id, pd.payment_account.id, pd.payment_date, context=context)

            move_obj.post(cr, uid, [move_id], context={})

        return {'type': 'ir.actions.act_window_close'}

class cash_pdocument (TransientModel):
    _name = 'account.cash_pdocument'

    def _get_default_journal(self, cr, uid, context=None):
        if context is None: context = {}
        j_id = context.get('journal_id', False)
        if not j_id:
            journal_obj = self.pool['account.journal']
            j_ids = journal_obj.search(cr, uid, [('type','=','purchase')], context=context)
            if j_ids and len(j_ids)==1:
                j_id = j_ids[0]
        return j_id
        
    def _get_docs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        doc_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = doc_ids
        return res

    _columns = {
        'docs': fields.function(_get_docs, method=True, 
                                type="one2many", relation="account.payable_document"),
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

        period_pool = self.pool.get('account.period')
        journal_pool = self.pool.get('account.journal')

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

        journal_obj = self.pool.get('account.journal')

        journal = journal_obj.browse(cr, uid, journal_id, context=context)
        res = {'cash_account': journal.default_debit_account_id and journal.default_debit_account_id.id or False}

        occd = self.onchange_cash_date (cr, uid, ids, cash_date, journal_id, context=context)
        if occd and 'value' in occd:
            res.update(occd['value'])

        return {'value': res}

    def action_cash_doc(self, cr, uid, ids, context=None):
        if not context: context = {}

        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')

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

            #Generate a pair of movements, 
            #one for the debit account of the journal and one for the credit account (by default, the credit account of the journal)

            for doc in cd.docs:
                move_line = {
                    'name': doc.name,
                    'journal_id': cd.journal.id,
                    'period_id': cd.period.id,
                    'account_id': cd.cash_account.id,
                    'move_id': move_id,
                    'partner_id': doc.payed_to.id,
                    'currency_id': company_currency_id != doc.currency.id and doc.currency.id or False,
                    'amount_currency': company_currency_id != doc.currency.id and doc.original_amount or 0.0,
                    'analytic_account_id': False,
                    'quantity': 1,
                    'debit': doc.amount,
                    'credit': 0.0,
                    'date_maturity': cd.cash_date,
                }

                move_line_obj.create(cr, uid, move_line, context=context)

                move_line.update({
                    'account_id': doc.payed_on_account.id,
                    'amount_currency': -move_line['amount_currency'],
                    'credit': doc.amount,
                    'debit': 0.0,
                })

                move_line_obj.create(cr, uid, move_line, context=context)

                doc.cash(cd.cash_date)

            move_obj.post(cr, uid, [move_id], context={})

        return {'type': 'ir.actions.act_window_close'}

class reject_document (TransientModel):
    _name = 'account.reject_pdocument'

    def _get_docs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        doc_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = doc_ids
        return res

    _columns = {
        'docs': fields.function(_get_docs, method=True, 
                                type="one2many", relation="account.payable_document"),
    }

    def action_reject_doc(self, cr, uid, ids, context=None):
        if not context: context = {}

        created_debit_notes = []

        for rd in self.browse (cr, uid, ids, context=context):
            invoice_obj = self.pool['account.invoice']
            invoice_line_obj = self.pool['account.invoice.line']

            for doc in rd.docs:
                vals = invoice_obj.default_get(cr, uid, [], context=context)
                vals['partner_id'] = doc.received_from.id
                vals['type'] = 'in_invoice'
                ocp = invoice_obj.onchange_partner_id(cr, uid, [], 
                                                      vals['type'],
                                                      vals['partner_id'])
                if ocp and 'value' in ocp:
                    vals.update(ocp['value'])

                vals['debit_note'] = True

                invoice_id = invoice_obj.create(cr, uid, vals, context=context)

                vals = invoice_line_obj.default_get(cr, uid, [], context=context)
                vals['invoice_id'] = invoice_id
                if not doc.company.pdoc_reject_service:
                    raise except_osv(_("Error"), 
                                     _("No default service for rejected documents defined for company [%s]!. Please check it") % doc.company.name)
                vals['product_id'] = doc.company.pdoc_reject_service.id
                vals['quantity'] = 1
                vals['price_unit'] = doc.amount
                vals['price_subtotal'] = doc.amount
                vals['account_id'] = doc.payed_on_account.id
                vals['name'] = _('Reject payable document %s') % doc.name_get()[0][1]
                invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)

                if doc.company.doc_reject_charge_service:
                    vals = invoice_line_obj.default_get(cr, uid, [], context=context)
                    vals['invoice_id'] = invoice_id
                    vals['product_id'] = doc.company.pdoc_reject_charge_service.id
                    vals['quantity'] = 1
                    vals['name'] = _('Processing charge, payable document %s') % doc.name_get()[0][1]
                    ocp = invoice_line_obj.product_id_change(
                                  cr, uid, [], vals['product_id'], False, qty=1, name=vals['name'], 
                                  type='in_invoice', partner_id=doc.received_from.id, 
                                  fposition_id=False, price_unit=False, 
                                  currency_id=doc.company.currency_id.id, 
                                  company_id=doc.company.id,
                                  context=context)
                    if ocp and 'value' in ocp:
                        vals.update(ocp['value'])
                    invoice_line_obj.create(cr, uid, vals, context=context)

                created_debit_notes.append(invoice_id)
                doc.reject(False)

        if created_debit_notes:
            models_data = self.pool.get('ir.model.data')

            # Get lead views
            dummy, form_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
            dummy, tree_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_supplier_tree')
            dummy, search_view = models_data.get_object_reference(cr, uid, 'account', 'view_account_invoice_supplier_filter')

            return {
                'name':_("Rejection debit notes"),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'context': {'default_type':'in_invoice', 'type':'in_invoice', 'journal_type': 'purchase'},
                'search_view_id': search_view,
                'domain': [('id','in',created_debit_notes)],
                'views': [(tree_view or False, 'tree'), (form_view or False, 'form')],
            }
        else:            
            return {'type': 'ir.actions.act_window_close'}

class get_back_document (TransientModel):
    _name = 'account.get_back_pdocument'

    def _get_docs(self, cr, uid, ids, fields, args, context=None):
        context = context or {}

        res = {}
        doc_ids = context.get('active_ids', [])
        for id in ids:
            res[id] = doc_ids
        return res

    _columns = {
        'docs': fields.function(_get_docs, method=True, 
                                type="one2many", relation="account.payable_document"),
    }

    def action_gb_doc(self, cr, uid, ids, context=None):
        if not context: context = {}

        created_debit_notes = []

        for gbd in self.browse (cr, uid, ids, context=context):
            invoice_obj = self.pool['account.invoice']
            invoice_line_obj = self.pool['account.invoice.line']

            for doc in gbd.docs:
                vals = invoice_obj.default_get(cr, uid, [], context=context)
                vals['partner_id'] = doc.received_from.id
                vals['type'] = 'in_invoice'
                ocp = invoice_obj.onchange_partner_id(cr, uid, [], 
                                                      vals['type'],
                                                      vals['partner_id'])
                if ocp and 'value' in ocp:
                    vals.update(ocp['value'])

                vals['debit_note'] = True

                invoice_id = invoice_obj.create(cr, uid, vals, context=context)

                vals = invoice_line_obj.default_get(cr, uid, [], context=context)
                vals['invoice_id'] = invoice_id
                if not doc.company.doc_reject_service:
                    raise except_osv(_("Error"), 
                                     _("No default service for rejected documents defined for company [%s]!. Please check it") % gbd.doc.company.name)
                vals['product_id'] = doc.company.pdoc_reject_service.id
                vals['quantity'] = 1
                vals['price_unit'] = doc.amount
                vals['price_subtotal'] = doc.amount
                vals['account_id'] = doc.payed_on_account.id
                vals['name'] = _('Get back payable document %s') % doc.name_get()[0][1]
                invoice_line_obj.create(cr, uid, vals, context=context)

                created_debit_notes.append(invoice_id)
                doc.get_back(False)

        if created_debit_notes:
            models_data = self.pool.get('ir.model.data')

            # Get lead views
            dummy, form_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
            dummy, tree_view = models_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
            dummy, search_view = models_data.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')

            return {
                'name':_("Getting back debit notes"),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'nodestroy': False,
                'context': {'default_type':'in_invoice', 'type':'in_invoice', 'journal_type': 'purchase'},
                'search_view_id': search_view,
                'domain': [('id','in',created_debit_notes)],
                'views': [(tree_view or False, 'tree'), (form_view or False, 'form')],
            }
        else:            
            return {'type': 'ir.actions.act_window_close'}

