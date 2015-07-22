# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2014 NUMA Extreme Systems (<http:www.numaes.com>).
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


from openerp.osv.osv import Model, except_osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
import time

import logging
_logger = logging.getLogger(__name__)

class account_move_line(Model):
    _inherit = 'account.move.line'
    
    def get_move_reference(self, cr, uid, ids, context=None):
        res = {}
        for aml in self.browse(cr, uid, ids, context=context):
            cr_obj = self.pool['account.customer_voucher']
            cr_ids = cr_obj.search(cr, uid, [('move','=',aml.move_id.id), ('cancelation_move','=',aml.move_id.id)])
            name = None
            if cr_ids:
                voucher = cr_obj.browse(cr, uid, cr_ids[0], context=context)
                mask = voucher.move == aml.move_id and _('CVOUCHER %s') or _('CVOUCHER CANC %s')
                name = mask % voucher.name
            if not name:
                super_res = super(account_move_line, self).get_move_reference(cr, uid, [aml.id], context=context)
                name = super_res[aml.id]
            res[aml.id] = name
            
        return res

class customer_voucher(Model):
    '''
    A customer voucher is the document that declares the reception of several values from a partner,
    as cash, credit card vouchers, bank transfers or documents (cheques)
    Those values become a credit of the partner with a maturity date (one different date for each document)
    '''


    def _get_name(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('default_name', '')

    def _get_journal(self, cr, uid, context=None):
        if context is None: context = {}
        j_id = context.get('default_journal', False)
        if not j_id:
            journal_obj = self.pool['account.journal']
            company_obj = self.pool['res.company']
            
            default_company_id = company_obj._company_default_get(cr, uid, 'account.account', context=context)
            if default_company_id:
                journal_ids = journal_obj.search(cr, uid,
                                                 [('company_id','=',default_company_id),
                                                  ('type','in',['sale'])],
                                                 context=context)
                if not journal_ids:
                    journal_ids = journal_obj.search(cr, uid,
                                                     [('company_id','=',default_company_id),
                                                      ('type','in',['sale_refund'])],
                                                     context=context)
                    if not journal_ids:
                        journal_ids = journal_obj.search(cr, uid,
                                                         [('company_id','=',default_company_id),
                                                          ('type','in',['general'])],
                                                         context=context)
                if journal_ids:
                    j_id = journal_ids[0]
        return j_id
        
    def _get_notes(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('default_notes', False)

    def _get_reference(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('default_reference', False)

    def _get_cash_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for cash in cv.cash_entries:
                amount += cash.amount
            res[cv.id] = amount
        return res

    def _get_bt_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for bt in cv.bt_entries:
                amount += bt.amount
            res[cv.id] = amount
        return res

    def _get_ccv_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for ccv in cv.ccv_entries:
                amount += ccv.amount
            res[cv.id] = amount
        return res

    def _get_doc_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for doc in cv.doc_entries:
                amount += doc.amount
            res[cv.id] = amount
        return res

    def _get_qm_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for qm in cv.qm_entries:
                amount += qm.amount
            res[cv.id] = amount
        return res

    def _get_debt_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for debt in cv.debt_entries:
                amount += debt.amount
            res[cv.id] = amount
        return res

    def _get_balance(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for cv in self.browse (cr, uid, ids, context=context):
            c = []
            for cash in cv.cash_entries:
                c.append({'amount': cash.amount})
            b = []
            for bt in cv.bt_entries:
                b.append({'amount': bt.amount})
            cc = []
            for ccv in cv.ccv_entries:
                cc.append({'amount': ccv.amount})
            q = []
            for qm in cv.qm_entries:
                q.append({'amount': qm.amount})
            d = []
            for doc in cv.doc_entries:
                d.append({'amount': doc.amount})
            db = []
            for debt in cv.debt_entries:
                db.append({'amount': debt.amount})

            res[cv.id] = self._compute_balance (cr, uid, c, b, cc, q, d, db)
        return res

    def _compute_balance(self, cr, uid, 
                            cash_entry_ids, 
                            bt_entry_ids, 
                            ccv_entry_ids, 
                            qm_entry_ids, 
                            doc_entry_ids, 
                            debt_entry_ids,
                            context=None):
        balance = 0.0
        for cash in cash_entry_ids:
            balance += cash['amount']
        for bt in bt_entry_ids:
            balance += bt['amount']
        for ccv in ccv_entry_ids:
            balance += ccv['amount']
        for qm in qm_entry_ids:
            balance += qm['amount']
        for doc in doc_entry_ids:
            balance += doc['amount']
        for debt in debt_entry_ids:
            balance -= debt['amount']

        return balance

    _name = 'account.customer_voucher'
    _description = 'Customer vouchers'
    _order = "date desc, id desc"
    _columns = {
        'name': fields.char('Refernnce', 
                            size=256, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'date': fields.date('Date', 
                            readonly=True, 
                            select=True, 
                            states={'draft':[('readonly',False)]}, 
                            help="Effective receipt date"),
        'period': fields.many2one('account.period', 'Period', 
                            required=True, readonly=True, 
                            states={'draft':[('readonly',False)]}, 
                            help="Effective date of the reconciliation"),
        'journal': fields.many2one('account.journal', 'Journal', 
                            required=True, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'account':fields.many2one('account.account', 'Account', 
                            required=True, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'company': fields.many2one('res.company', 'Company', 
                            required=True, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'currency': fields.related('company','currency_id',
                            type='many2one', 
                            relation='res.currency', 
                            string='Currency', 
                            store=False, 
                            readonly=True),

        'state':fields.selection(
            [('draft','Draft'),
             ('posted','Posted'),
             ('canceled','Canceled')
            ], 'State', readonly=True, size=32,
            help=' * \'Draft\' state is used on new document entries. \
                        \n* \'Posted\' is used when the document is registered and account moves are generated \
                        \n* \'Canceled\' is used for canceled documents.'),

        'notes':fields.text('Notes', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'reference': fields.char('Ref #', 
                            size=64, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}, 
                            help="Reference number."),
        'unassigned_payments': fields.float('Unassigned payments', 
                            digits=(16,2), 
                            help="Acumulated payments, registered but not assigned to any document"),
        'to_be_checked': fields.boolean('To be checked'),
        'move': fields.many2one('account.move', 
                                'Account move', 
                                readonly=True),
        'cancelation_move': fields.many2one('account.move', 
                                            'Cancelation accounting move', 
                                            readonly=True),
        'partner': fields.many2one('res.partner', 
                            'Customer', 
                            change_default=1, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'audit': fields.related('move', 'to_check', 
                            type='boolean', 
                            relation='account.move', 
                            string='Audit ?'),

        'balance': fields.function(_get_balance, method=True, 
                            string='Balance', 
                            type='float', 
                            readonly=True),
        'cash_total': fields.function(_get_cash_total, method=True, 
                            string='Total cash', 
                            type='float', 
                            readonly=True),
        'bt_total': fields.function(_get_bt_total, method=True, 
                            string='Total transfers', 
                            type='float', 
                            readonly=True),
        'ccv_total': fields.function(_get_ccv_total, method=True,
                            string='Total credit card vouchers',
                            type="float",
                            readonly=True),
        'qm_total': fields.function(_get_qm_total, 
                            method=True, 
                            string='Total retentions', 
                            type='float', 
                            readonly=True),
        'doc_total': fields.function(_get_doc_total, 
                            method=True, 
                            string='Total documents', 
                            type='float', 
                            readonly=True),
        'debt_total': fields.function(_get_debt_total, 
                            method=True, 
                            string='Total debts', 
                            type='float', 
                            readonly=True),

        'cash_entries':fields.one2many('account.cv_cash',
                            'cv',
                            'Cash', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'bt_entries':fields.one2many('account.cv_bank_transfer',
                            'cv',
                            'Bank transfers', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'ccv_entries':fields.one2many('account.cv_credit_card_voucher',
                            'cv',
                            'Credit card vouchers', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'qm_entries':fields.one2many('account.cv_quick_move',
                            'cv',
                            'Received retentions', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'doc_entries':fields.one2many('account.cv_doc',
                            'cv',
                            'Received documents', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'debt_entries':fields.one2many('account.cv_debt',
                            'cv',
                            'Applied debts', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
    }

    _defaults = {
        'name':_get_name,
        'journal':_get_journal,
        'reference': _get_reference,
        'state': 'draft',
        'name': '',
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        cvs = self.browse (cr, SUPERUSER_ID, ids, context=context)
        return [(cv.id, "%s [%s]" % (cv.name or 'Draft', cv.company.name)) for cv in cvs]

    def onchange_lines(self, cr, uid, ids, 
                            cash_entry_ids, 
                            bt_entry_ids, 
                            qm_entry_ids, 
                            doc_entry_ids, 
                            ccv_entry_ids,
                            debt_entry_ids, 
                            context=None):

        c  = self.resolve_2many_commands(cr, uid, 'cash_entries', cash_entry_ids, ['amount'], context=context)
        b  = self.resolve_2many_commands(cr, uid, 'bt_entries',   bt_entry_ids,   ['amount'], context=context)
        cv = self.resolve_2many_commands(cr, uid, 'ccv_entries',  ccv_entry_ids,  ['amount'], context=context)
        q  = self.resolve_2many_commands(cr, uid, 'qm_entries',   qm_entry_ids,   ['amount'], context=context)
        d  = self.resolve_2many_commands(cr, uid, 'doc_entries',  doc_entry_ids,  ['amount'], context=context)
        db = self.resolve_2many_commands(cr, uid, 'debt_entries', debt_entry_ids, ['amount'], context=context)

        return {'value': {'balance': self._compute_balance(cr, uid, c, b, cv, q, d, db)}}

    def onchange_company(self, cr, uid, ids, 
                            company_id, journal_id, partner_id, period_id, date,
                            context=None):
        journal_obj = self.pool['account.journal']
        partner_obj = self.pool['res.partner']
        period_obj  = self.pool['account.period']
        user_obj = self.pool['res.users']
        company_obj = self.pool['res.company']

        res = {}
        domain = {}

        if company_id:
            company = company_obj.browse(cr, uid, company_id, context=context)
            if journal_id:
                journal = journal_id and journal_obj.browse(cr, uid, journal_id, context=context) or None
                if journal.company_id.id != company_id:
                    journal_ids = journal_obj.search(cr, uid, 
                                        [('company_id','=',company_id),('type','=','sale')],
                                        context=context)
                    if journal_ids and len(journal_ids) == 1:
                        journal_id = journal_ids[0]
                        journal = journal_obj.browse(cr, uid, journal_id, context=context)
                    else:
                        journal_id = False
                        
            if period_id:
                period = period_id and period_obj.browse(cr, uid, period_id, context=context) or None
                if period.fiscalyear_id.company_id.id != company_id:
                    period_ids = period_obj.search(cr, uid, 
                                        [('fiscalyear_id.company_id','=',company_id),
                                         ('state','=','draft'),
                                         ('date_start','<=', date),
                                         ('date_stop','>=', date)],
                                        context=context)
                    if period_ids and len(period_ids) == 1:
                        period_id = period_ids[0]
                    else:
                        period_id = False
                        
            res['journal'] = journal_id
            res['period'] = period_id
            res['debt_entries'] = []
            res['currency'] = company.currency_id.id

            if partner_id:
                user = user_obj.browse(cr, uid, uid, context=context)
                saved_company = None
                if user.company_id.id != company_id:
                    saved_company = user.company_id
                    user.write({'company_id': company_id})
                partner = partner_obj.browse(cr, uid, partner_id, context=context)
                res['account'] = partner.property_account_receivable.id
                if saved_company:
                    user.write({'company_id': saved_company})

            domain['journal'] = [('type','in',['sale']), ('company_id','=',company_id)]
            domain['period']  = [('fiscalyear_id.company_id','=',company_id)]
            domain['account'] = [('company_id','=', company_id)]
        else:
            res['journal'] = False
            res['period'] = False
            res['debt_entries'] = []
            res['account'] = False

            domain['journal'] = [('type','in',['sale'])]
            domain['period']  = []
            domain['account'] = []

        res['cash_ids'] = []
        res['bt_ids'] = []
        res['ccv_ids'] = []
        res['qm_ids'] = []
        res['doc_ids'] = []
        res['debt_ids'] = []
        res['cash_total'] = 0.0
        res['bt_total'] = 0.0
        res['ccv_total'] = 0.0
        res['qm_total'] = 0.0
        res['doc_total'] = 0.0
        res['debt_total'] = 0.0

        return {'value': res, 'domain': domain}

    def onchange_journal(self, cr, uid, ids, 
                          journal_id, date,
                          context=None):
        res = {}
        if journal_id:
            res['balance']  = 0.0

        res['cash_ids'] = []
        res['bt_ids'] = []
        res['ccv_ids'] = []
        res['qm_ids'] = []
        res['doc_ids'] = []
        res['debt_ids'] = []
        res['cash_total'] = 0.0
        res['bt_total'] = 0.0
        res['ccv_total'] = 0.0
        res['qm_total'] = 0.0
        res['doc_total'] = 0.0
        res['debt_total'] = 0.0

        return {'value': res}

    def onchange_partner(self, cr, uid, ids, 
                            partner_id, 
                            company_id,  
                            period_id,
                            journal_id, 
                            date,
                            context=None):
        return self.onchange_company(cr, uid, ids, 
                            company_id, journal_id, partner_id, period_id, date,
                            context=context)

    def onchange_date(self, cr, uid, ids, 
                       date, period_id, partner_id, 
                       currency_id, company_id, 
                       context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if not date or not company_id:
            return False

        if not context: context = {}

        period_obj = self.pool['account.period']
        
        default = {'value':{}}

        pids = period_obj.search(cr, uid, 
                                  [('state', '=', 'draft'),
                                   ('date_start', '<=', date), 
                                   ('date_stop', '>=', date), 
                                   ('company_id', '=', company_id)],
                                  context=context)

        if not pids:
            raise except_osv(_('Error!'), 
                                 _('No period for the given date!'))
            
        period_id = pids[0]
        default['value'] = {'period': period_id}

        return default

    def get_lookup_criteria(self, cr, uid, ids, 
                             partner_id, company_id, fiscalyear_id, 
                             context=None):
        return [ ('move_id.state','=','posted'), 
                 ('account_id.type', '=', 'receivable'),
                 ('reconcile_id', '=', False), 
                 ('partner_id', 'child_of', [partner_id]), 
                 ('company_id', '=', company_id)]
                 
    def action_print(self,cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        return self.pool['report'].get_action(cr, uid, ids, 'customer_voucher_print', context=context)

    def action_get_debts(self, cr, uid, ids, context=None):
        currency_obj = self.pool['res.currency']
        move_line_obj = self.pool['account.move.line']

        for cv in self.browse(cr, uid, ids, context=context):
            if (not cv.period) or (not cv.company) or (not cv.currency) or (not cv.partner):
                continue

            if cv.state != 'draft':
                continue
                
            company = cv.company
            company_currency = company.currency_id
            period = cv.period

            if period.state != 'draft':
                raise except_osv(_('Error!'), _('Period is not open. Please check it!'))

            domain = self.get_lookup_criteria(cr, uid, [cv.id], 
                                              cv.partner.id, 
                                              cv.company.id, 
                                              period.fiscalyear_id.id, 
                                              context=context)

            for debt in cv.debt_entries:
                debt.unlink()
                
            ids = move_line_obj.search (cr, uid, domain, context=context)
            raw_moves = move_line_obj.browse(cr, uid, ids, context=context)

            unreconciled = filter(lambda m: not m.reconcile_partial_id, raw_moves)
            reconcile_list = list(set([m.reconcile_partial_id for m in filter(lambda m: m.reconcile_partial_id, raw_moves)]))
            reconciled = [max(r.line_partial_ids, key=lambda m: m.debit or m.credit) for r in reconcile_list]
            
            moves = unreconciled + reconciled
            moves.sort(key=lambda move: move.date_maturity or move.date)
                
            debts = []
            unassigned_credit = 0.0
            for line in moves:
                if line.credit:
                    unassigned_credit += line.amount_residual
                    continue
                    
                amount_unreconciled = abs(line.amount_residual)

                if currency_obj.is_zero(cr, uid, company_currency, amount_unreconciled):
                    if line.reconcile_partial_id:
                        line.reconcile_partial_id.reconcile_partial_check(context=context)
                    continue

                rs = {
                    'cv': cv.id,
                    'move_line':line.id,
                    'amount' : 0.0,
                }
                debts.append((0, 0, rs))

            if debts or unassigned_credit:
                cv.write({
                    'unassigned_payments' : unassigned_credit,
                    'debt_entries': debts})

        return True

    def action_reasign_credit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for cv in self.browse (cr, uid, ids, context=context):
            if (not cv.period) or (not cv.company) or (not cv.currency) or (not cv.partner):
                continue

            if cv.state != 'draft':
                continue

            total_credit = 0.0
            for cash in cv.cash_entries:
                total_credit += cash.amount
            for bt in cv.bt_entries:
                total_credit += bt.amount
            for ccv in cv.ccv_entries:
                total_credit += ccv.amount
            for qm in cv.qm_entries:
                total_credit += qm.amount
            for doc in cv.doc_entries:
                total_credit += doc.amount

            new_balance = total_credit
            debts = []
            moves = list(cv.debt_entries)
            moves.sort(key=lambda move: move.maturity_date or move.original_date)
                
            for line in moves:
                amount = min(line.unreconciled_amount, total_credit)
                debts.append((1, line.id, {'amount' : amount}))

                if total_credit > amount:
                    total_credit -= amount
                else:
                    total_credit = 0.0

                new_balance -= amount

            cv.write({'debt_entries': debts})

        return True

    def action_reset_amount(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for cv in self.browse (cr, uid, ids, context=context):
            for line in cv.debt_entries:
                line.write({'amount' : 0.0})

        return True

    def action_cancel(self, cr, uid, ids, context=None):
        move_obj = self.pool['account.move']

        for cv in self.browse(cr, uid, ids, context=context):
            if cv.state not in ['done']:
                continue
            val = {
                'state':'canceled',
                'cancel_move': cv.move and \
                    move_obj.revert(cr, uid, [cv.move.id], 
                                    {'name': cv.name,
                                     'ref': _('CANCELATION'),
                                     'date': fields.date.context_today(self, cr, uid, context=context)}, 
                                     context=context)[cv.move.id] or False, 
            }
            cv.write(val)

        return True

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] in ['posted', 'canceled']:
                raise except_osv(_('Error!'), 
                      _('Posted or canceled vouchers could not be deleted!'))
        return super(customer_voucher, self).unlink(cr, uid, ids, context=context)

    def action_post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool['account.move']
        move_line_obj = self.pool['account.move.line']
        user_obj = self.pool['res.users']
        sequence_obj = self.pool['ir.sequence']

        def process_debt(amount_to_apply, 
                         already_applied, 
                         voucher,
                         applicable_debts,  
                         source_name, 
                         source_partner, 
                         source_account, 
                         source_move_id, 
                         source_currency,
                         source_currency_amount,
                         maturity_date,
                         source_tax_code = False,
                         source_tax_amount = 0.0):

            original_amount = amount_to_apply

            move_line = {
                'name': source_name,
                'account_id': source_account.id,
                'move_id': source_move_id,
                'partner_id': source_partner.id,
                'currency_id': company_currency != source_currency and \
                               source_currency.id or False,
                'amount_currency': company_currency != source_currency and \
                                   -(amount_to_apply/original_amount * source_currency_amount) or False,
                'amount_currency': 0.0,
                'analytic_account_id': False,
                'quantity': 1,
                'debit': amount_to_apply,
                'credit': 0.0,
                'date': voucher.date,
                'date_maturity': maturity_date,
                'tax_code_id': source_tax_code and source_tax_code.id or False,
                'tax_amount': source_tax_amount,
            }

            move_1 = move_line_obj.create(cr, uid, 
                                    move_line, check=False, 
                                    context=ncontext)

            while amount_to_apply > 0.01 and len(applicable_debts) > 0:
                #Apply this amount to debts not yet covered
                #Taking the amount to apply, try to cover as many docs as possible
                #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed

                debt = applicable_debts[0]
                to_apply = min(amount_to_apply, debt.amount - already_applied)
                
                _logger.debug("Procesando deuda %s, por aplicar %f, a aplicar en esta deuda %f, ya aplicado %f" % (debt.move_line.name, amount_to_apply, to_apply, already_applied))

                move_line.update({
                    'partner_id': source_partner.id,
                    'date': voucher.date,
                    'date_maturity': maturity_date,
                })
                
                if to_apply >= 0.01:
                    #Generate a counter movement for the debt
                    
                    move_line.update({
                        'name': source_name,
                        'account_id': debt.account.id,
                        'amount_currency': move_line['amount_currency'] and \
                                           -move_line['amount_currency'] or 0.0,
                        'debit': 0.0,
                        'credit': to_apply,
                    })

                    move_2 = move_line_obj.create(cr, uid, 
                                            move_line, check=False, 
                                            context=ncontext)

                    if debt.move_line.partner_id != voucher.partner:
                        move_line.update({
                            'partner_id': voucher.partner.id,
                            'account_id': source_account.id,
                            'date': voucher.date,
                            'date_maturity': maturity_date,
                            'name': _('Transfer'),
                            'debit': to_apply,
                            'credit': 0.0,
                        })
                        new_line3_id = move_line_obj.create (cr, uid, 
                                                    move_line, check=False, 
                                                    context=ncontext)

                        move_line.update({
                            'partner_id': debt.move_line.partner_id.id,
                            'account_id': debt.move_line.account_id.id,
                            'debit': 0.0,
                            'credit': to_apply,
                        })
                        new_line4_id = move_line_obj.create (cr, uid, 
                                                    move_line, check=False, 
                                                    context=ncontext)

                        reconcile_lines.append([debt.move_line.id, new_line4_id])
                        reconcile_lines.append([move_2, new_line3_id])
                    else:    
                        reconcile_lines.append([debt.move_line.id, move_2])
                        
                    amount_to_apply -= to_apply
                    already_applied += to_apply

                if to_apply <= 0.01 or already_applied >= debt.amount:
                    applicable_debts.pop(0)
                    already_applied = 0.0

            if amount_to_apply > 0.01:
                move_line = {
                    'name': source_name,
                    'account_id': voucher.account.id,
                    'move_id': source_move_id,
                    'partner_id': voucher.partner.id,
                    'currency_id': False,
                    'amount_currency': 0.0,
                    'analytic_account_id': False,
                    'quantity': 1,
                    'date': voucher.date,
                    'date_maturity': maturity_date,
                    'tax_code_id': False,
                    'tax_amount': False,
                    'debit': 0.0,
                    'credit': amount_to_apply,
                }

                move_line_obj.create(cr, uid, move_line, check=False, context=ncontext)

            return already_applied, move_1

        user = user_obj.browse(cr, uid, uid, context=context)
        saved_company = user.company_id

        for v in self.browse(cr, uid, ids, context=context):
            if v.move:
                continue

            user.write({'company_id': v.company.id})
            voucher = self.browse(cr, uid, v.id, context=context)

            context_multi_currency = context.copy()
            context_multi_currency.update({'date': voucher.date})

            if voucher.name == '/' or not voucher.name:
                name = sequence_obj.get(cr, uid, 'customer_voucher') or '/'

            voucher.write ({'name': name})
            voucher.refresh()

            #Compute the total amount to be payed
            total_credit = 0.0

            for cash in voucher.cash_entries:
                total_credit += cash.amount

            for bt in voucher.bt_entries:
                total_credit += bt.amount

            for ccv in voucher.ccv_entries:
                total_credit += ccv.amount
                if ccv.ccv.state not in ['data_complete','draft']:
                    raise except_osv(_('Error !'), 
                                     _('Credit card voucher [%s] is not longer in data complete state!. Please check it!') % \
                                     ccv.ccv.name)

            for qm in voucher.qm_entries:
                total_credit += qm.amount

            for doc in voucher.doc_entries:
                total_credit += doc.amount
                if doc.doc.state not in ['data_complete', 'draft']:
                    raise except_osv(_('Error !'), 
                                     _('Document [%s] is not longer in data complete state!. Please check it!') % \
                                     doc.doc.name)

            for debt in voucher.debt_entries:
                if debt.amount < 0 or debt.amount > debt.unreconciled_amount:
                    raise except_osv(_('Error !'), 
                                     _('Debt [%s], amount to apply should be positive and not larger than the open amount. Please check it!') % \
                                     debt.name)

            if total_credit == 0:
                    raise except_osv(_('Not complete!'),
                        _('No credit entered!'))

            voucher.write ({'name': name})

            move = {
                'name': name,
                'ref': voucher.reference or name,
                'journal_id': voucher.journal.id,
                'narration': voucher.notes,
                'date': voucher.date,
                'period_id': voucher.period.id,
            }
            move_id = move_obj.create(cr, uid, move, context=context)
            move = move_obj.browse(cr, uid, move_id, context=context)

            company_currency = voucher.company.currency_id

            already_applied = 0.0
            applicable_debts = []
            for line in voucher.debt_entries:
                if line.amount:
                    applicable_debts.append(line)

            reconcile_lines = []
            ncontext=context.copy()
            ncontext['period_id'] = voucher.period.id
            ncontext['journal_id'] = voucher.journal.id

            # Process cash

            for cash in voucher.cash_entries:
                _logger.debug("Cash, amount %f" % cash.amount)

                already_applied, aml_id = \
                process_debt(cash.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             _('Cash'), 
                             voucher.partner, 
                             voucher.journal.default_credit_account_id, 
                             move_id,
                             cash.currency,
                             cash.original_amount,
                             voucher.date,
                             False,
                             False)

            #Process bank transfers entries
            for bt in voucher.bt_entries:
                _logger.debug("Bank transfer %s, amount %f" % (bt.reference, bt.amount))

                already_applied, aml_id = \
                process_debt(bt.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             "%s-%s" % (bt.bank_account.owner_name or '', bt.bank_account.bank_name or ''), 
                             voucher.partner, 
                             bt.account, 
                             move_id,
                             bt.currency,
                             bt.original_amount,
                             bt.transfer_date,
                             False,
                             False)

            #Process credit card entries

            for ccv in voucher.ccv_entries:
                _logger.debug("Credit card voucher %s, amount %f" % (ccv.ccv.name, ccv.amount))

                already_applied, aml_id = \
                process_debt(ccv.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             "%s-%s" % (ccv.credit_account.name or '', ccv.ccv.name or ''), 
                             voucher.partner, 
                             ccv.credit_account, 
                             move_id,
                             ccv.currency,
                             ccv.original_amount,
                             voucher.date,
                             False,
                             False)

                ccv.ccv.write({'received_on_account': ccv.credit_account.id,
                               'received_on': voucher.date})             
                ccv.ccv.receive()

            #Process quick moves

            for qm in voucher.qm_entries:
                _logger.debug("Quick Move %s, amount %f" % (qm.qm.name, qm.amount))

                already_applied, aml_id = \
                process_debt(qm.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             qm.qm.name or _('Quick Move'), 
                             voucher.partner, 
                             qm.credit_account, 
                             move_id,
                             company_currency,
                             0.0,
                             voucher.date,
                             False,
                             False)

            #Process received documents
                
            for doc in voucher.doc_entries:
                _logger.debug("Document %s, amount %f" % (doc.doc.name, doc.amount))

                already_applied, aml_id = \
                process_debt(doc.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             "%s-%s" % (doc.doc.issuer_account.bank_name, doc.doc.name), 
                             voucher.partner, 
                             doc.credit_account, 
                             move_id,
                             doc.currency,
                             doc.original_amount,
                             doc.maturity_date,
                             False,
                             False)

                doc.doc.write({'received_on_account': doc.credit_account.id})             
                doc.doc.receive()
                
            #NUMA
            #print "==================================================================================="
            #move = move_obj.browse(cr, uid, move_id)
            #for ml in move.line_id:
            #    print ml.account_id.name, ml.debit, ml.credit, ml.reconcile_id.name, ml.reconcile_partial_id.name

            move_obj.post(cr, uid, [move_id], context={})

            if reconcile_lines:
                for move_set in reconcile_lines:
                    if len(move_set) >= 2:
                        move_line_obj.reconcile_partial(cr, uid, move_set)

            voucher.write({'state': 'posted', 'move': move_id})

        user.write({'company_id': saved_company.id})

        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state': 'draft',
            'number': False,
            'move_id': False,
            'cash_ids': False,
            'bt_ids': False,
            'qm_ids': False,
            'doc_ids': False,
            'debt_ids': False,
            'reference': False
        })
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(customer_voucher, self).copy(cr, uid, id, default, context)

class cv_cash(Model):
    _name = 'account.cv_cash'
    _description = 'Received cash'

    def _get_currency(self, cr, uid, context=None):
        if not context: context = {}
        return context.get('default_currency', False)

    _columns = {
        'cv':fields.many2one('account.customer_voucher', 'Customer voucher', ondelete='cascade'),
        'currency': fields.many2one('res.currency','Currency', required=True),
        'original_amount':fields.float('Amount on original currency', digits_compute=dp.get_precision('Account'), required=True),
        'exchange_rate':fields.float('Exchange rate', digits_compute=dp.get_precision('Account'), required=True),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'analytic_account':fields.many2one('account.analytic.account', 'Analytic account'),
     }
    
    _defaults = {
        'currency': _get_currency,
    }
    
    def create (self, cr, uid, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (cv_cash, self).create (cr, uid, vals, context=context)

    def write (self, cr, uid, ids, vals, context=None):
        vals = vals or {}
        if 'original_amount' in vals or 'exchange_rate' in vals:
            vals['exchange_rate'] = vals['original_amount'] * vals['exchange_rate']
        return super (cv_cash, self).write (cr, uid, ids, vals, context=context)

    def onchange_currency (self, cr, uid, ids, currency_id, original_amount, cv_currency_id, context=None):
        if not context: context={}
        
        if not cv_currency_id:
            raise except_osv(_("Error!"),
                _("No currency defined. Probably you didn't select the company yet! Please check"))
                
        if not currency_id:
            return False
            
        currency_obj = self.pool['res.currency']
        from_currency = currency_obj.browse (cr, uid, currency_id, context=context)
        to_currency = currency_obj.browse (cr, uid, cv_currency_id, context=context)
        return {'value': {
                    'exchange_rate': currency_obj._get_conversion_rate (
                                        cr, uid, from_currency, to_currency, 
                                        context=context),
                    'amount': currency_obj.compute (
                                        cr, uid, currency_id, cv_currency_id, original_amount, 
                                        context=context),
                }}

    def onchange_exchange_rate (self, cr, uid, ids, exchange_rate, original_amount, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

    def onchange_original_amount (self, cr, uid, ids, original_amount, exchange_rate, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

class cv_bt(Model):
    _name = 'account.cv_bank_transfer'
    _description = 'Received bank transfer'

    def _get_currency (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('default_currency', False)

    def _get_transfer_date (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('transfer_date', fields.date.context_today(self, cr, uid, context=context))

    _columns = {
        'cv':fields.many2one('account.customer_voucher', 'Customer voucher', ondelete='cascade'),
        'reference': fields.char('Ref #', size=64, help="Reference number."),
        'bank_account':fields.many2one('res.partner.bank', 'Bank Account', required=True),
        'account': fields.many2one('account.account', 'Account', required=True),
        'currency': fields.many2one('res.currency','Currency', required=True),
        'original_amount':fields.float('Original amount', digits_compute=dp.get_precision('Account'), required=True),
        'exchange_rate':fields.float('Exchange rate', digits_compute=dp.get_precision('Account'), required=True),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
        'transfer_date':fields.date('Transfer date', select=True, help="Effective transfer date, according to bank"),
        'analytic_account':fields.many2one('account.analytic.account', 'Analytic account'),
     }

    _defaults = {
        'currency': _get_currency,
        'transfer_date': _get_transfer_date,
    }

    def create (self, cr, uid, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (cv_bt, self).create (cr, uid, vals, context=context)

    def write (self, cr, uid, ids, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (cv_bt, self).write (cr, uid, ids, vals, context=context)
        
    def onchange_bank_account(self, cr, uid, ids, bank_account_id, context=None):
        bank_obj = self.pool['res.partner.bank']
        
        if bank_account_id:
            bank_account = bank_obj.browse (cr, uid, bank_account_id, context=context)
            if (not bank_account.journal_id) or (not bank_account.journal_id.default_credit_account_id):
                raise except_osv(_("Configuration error!"),
                    _("No journal or default account defined on bank account for credit or debit entries!. Please configure them or select another account!"))
            return {'value': {'account': bank_account.journal_id.default_credit_account_id.id}}
        return False

    def onchange_currency (self, cr, uid, ids, 
                              currency_id, original_amount, cv_currency_id, 
                              context=None):
        if not context: context={}

        if not cv_currency_id:
            raise except_osv(_("Error!"),
                _("No currency defined. Probably you didn't select the company yet! Please check"))
                
        if not currency_id:
            return
            
        currency_obj = self.pool['res.currency']
        from_currency = currency_obj.browse (cr, uid, currency_id, context=context)
        if cv_currency_id:
            to_currency = currency_obj.browse (cr, uid, cv_currency_id, context=context)
            return {'value': {
                        'exchange_rate': currency_obj._get_conversion_rate (
                                            cr, uid, from_currency, to_currency, 
                                            context=context),
                        'amount': currency_obj.compute (
                                            cr, uid, currency_id, cv_currency_id, original_amount, 
                                            context=context),
                    }}
        return False

    def onchange_exchange_rate (self, cr, uid, ids, exchange_rate, original_amount, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

    def onchange_original_amount (self, cr, uid, ids, original_amount, exchange_rate, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

class cv_qm(Model):
    _name = 'account.cv_quick_move'
    _description = 'Document receipt Retentions'
    _order = "description"

    _columns = {
        'cv':fields.many2one('account.customer_voucher', 'Customer Voucher', ondelete='cascade'),
        'qm':fields.many2one('account.quick_move', 'Code', required=True),
        'credit_account':fields.many2one('account.account', 'Credit account', required=True),
        'analytic_account':fields.many2one('account.analytic.account', 'Analitic account'),
        'description':fields.char('Description', size=256),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
        'analytic_account':fields.many2one('account.analytic.account', 'Analytic account'),
     }

    def onchange_qm (self, cr, uid, ids, qm_id, company_id, context = None):
        if not context: context = {}

        if not qm_id or not company_id:
            return False

        qm_obj = self.pool['account.quick_move']
        user_obj = self.pool['res.users']

        user = user_obj.browse(cr, uid, uid, context=context)
        saved_company = None
        if user.company_id.id != company_id:
            saved_company = user.company_id.id
            user.write({'company_id': company_id})
        qm = qm_obj.browse(cr, uid, qm_id, context=context)
        if saved_company:
            user.write({'company_id': saved_company.id})

        res = {'value': {
                 'credit_account': qm.property_qm_credit_account.id,
                 'analytic_account': qm.property_qm_analytic_account and qm.property_qm_analytic_account.id or False,
                 'description': qm.description,
                }}
        return res

class cv_ccv(Model):
    _name = 'account.cv_credit_card_voucher'
    _description = 'Customer voucher Credit Card vouchers'
    _order = "description"

    _columns = {
        'cv':fields.many2one('account.customer_voucher', 'Customer voucher', ondelete='cascade'),
        'ccv':fields.many2one('account.credit_card_voucher', 'Credit card voucher', required=True),
        'credit_account':fields.many2one('account.account', 'Credit account', required=True),
        'analytic_account':fields.many2one('account.analytic.account', 'Analytic account'),
        'description':fields.char('Description', size=256),
        'currency': fields.many2one('res.currency','Currency', required=True),
        'original_amount':fields.float('Original amount', digits_compute=dp.get_precision('Account'), required=True),
        'exchange_rate':fields.float('Exchange rate', digits_compute=dp.get_precision('Account'), required=True),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
    }

    def onchange_ccv (self, cr, uid, ids, ccv_id, company_id, context = None):
        if not context: context = {}

        if not ccv_id or not company_id:
            return False

        ccv_obj = self.pool['account.credit_card_voucher']
        user_obj = self.pool['res.users']

        user = user_obj.browse(cr, uid, uid, context=context)
        saved_company = None
        if user.company_id.id != company_id:
            saved_company = user.company_id.id
            user.write({'company_id': company_id})
        ccv = ccv_obj.browse(cr, uid, ccv_id, context=context)

        if saved_company:
            user.write({'company_id': saved_company.id})

        res = {}

        res['original_amount'] = ccv.original_amount
        res['exchange_rate'] = ccv.original_amount and ccv.amount / ccv.original_amount or 0.0
        res['amount'] = ccv.amount
        res['credit_account'] = ccv.cc_account.receive_account.id
        res['analytic_account'] = False
        res['description'] = "%s: %s" % (ccv.cc_account.name,ccv.name)
        res['currency'] =  ccv.currency and ccv.currency.id or False
        return {'value': res}

    def onchange_exchange_rate (self, cr, uid, ids, exchange_rate, original_amount, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

class cv_doc(Model):
    _name = 'account.cv_doc'
    _description = 'Customer voucher Document'
    _order = "description"

    _columns = {
        'cv':fields.many2one('account.customer_voucher', 'Customer voucher', ondelete='cascade'),
        'doc':fields.many2one('account.document', 'Document', required=True),
        'original_amount': fields.related('doc', 'original_amount', 
                                          string="Original amount", type="float",
                                          readonly=True),
        'currency': fields.related('doc', 'currency',
                                    string="Currency", type="many2one", relation="res.currency",
                                    readonly=True),
        'maturity_date': fields.related('doc', 'maturity_date',
                                    string="Maturity date", type="date",
                                    readonly=True),
        'exchange_rate': fields.float('Exchange rate', digits=(8,3)),
        'credit_account':fields.many2one('account.account', 'Credit account', required=True),
        'analytic_account':fields.many2one('account.analytic.account', 'Analitic account'),
        'description':fields.char('Description', size=256),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
    }

    def onchange_doc (self, cr, uid, ids, doc_id, company_id, context = None):
        if not context: context = {}

        if not doc_id or not company_id:
            return False

        doc_obj = self.pool['account.document']
        company_obj = self.pool['res.company']

        doc = doc_obj.browse(cr, uid, doc_id, context=context)

        company = company_obj.browse(cr, uid, company_id, context=context)
        tdoc_account = company.t_docs_account
        if not tdoc_account:
            raise except_osv(_("Configuration error!"),
                _("No account defined on [Account for received documents] for company %s!") % company.name)
        
        ntdoc_account = company.nt_docs_account
        if not ntdoc_account:
            raise except_osv(_("Configuration error!"),
                _("No account defined on [Account for not transferable received documents] for company %s!") % company.name)

        if doc.transferable:
            account = tdoc_account
        else:
            account = ntdoc_account

        res = {'value': {
                 'credit_account': account.id,
                 'analytic_account_id': False,
                 'description': "%s: %s" % (doc.issuer_account.name, doc.name),
                 'original_amount': doc.original_amount,
                 'exchange_rate': doc.original_amount and doc.amount / doc.original_amount or 0.0,
                 'maturity_date': doc.maturity_date,
                 'amount': doc.amount,
                }}

        return res

    def onchange_exchange_rate (self, cr, uid, ids, exchange_rate, original_amount, context=None):
        if not context: context={}

        return {'value': {
                    'amount': (original_amount or 0.0) * (exchange_rate or 0.0),
                }}

class cv_debt(Model):
    _name = 'account.cv_debt'
    _description = 'Customer voucher Debts'
    _order = "maturity_date"

    _columns = {
        'cv': fields.many2one('account.customer_voucher', 'Customer voucher', ondelete='cascade'),
        'move_line': fields.many2one('account.move.line', 'Move line', ondelete='restrict'),
        'ref': fields.related('move_line','ref', 
                             string="Reference", 
                             type="char", 
                             readonly=True),
        'account': fields.related('move_line', 'account_id',
                                 string="Account",
                                 type="many2many", relation="account.account",
                                 readonly=True),
        'partner': fields.related('move_line', 'partner_id',
                                 string="Customer",
                                 type="many2one", relation="res.partner",
                                 readonly=True),
        'original_amount': fields.related('move_line', 'debit',
                                          string="Original amount",
                                          type="float", digits_compute=dp.get_precision('Account'), 
                                          readonly=True), 
        'original_date': fields.related('move_line','date', 
                                        string="Date", 
                                        type='date', 
                                        readonly=True),
        'maturity_date': fields.related('move_line','date_maturity',
                                   string="Maturity date",
                                   type="date",
                                   readonly=True,
                                   store=True),
        'unreconciled_amount': fields.related('move_line', 'amount_residual',
                                              string="Residual ammount",
                                              type="float", digits_compute=dp.get_precision('Account'), 
                                              readonly=True), 
        'analytic_account': fields.related('move_line', 'analytic_account_id',
                                           string="Analytic account",
                                           type="many2one", relation='account.analytic.account', 
                                           readonly=True),
        'company': fields.related('move_line','move_id','company_id', 
                                  string="Company",
                                  type="many2one", relation='res.company', 
                                  readonly=True),
        'amount':fields.float('Amount to be applied', digits_compute=dp.get_precision('Account')),
    }

    def onchange_move_line(self, cr, uid, ids, move_line_id, context=None):
        aml_obj = self.pool['account.move.line']

        res = {}
        if move_line_id:
            aml = aml_obj.browse(cr, uid, move_line_id, context=context)

            if aml.status != 'valid':
                raise except_osv(_("Error!"),
                                 _("Move line is not valid! Please check it"))

            res['partner'] = aml.partner.ids
            amount = aml.debit or -aml.credit
            res['account'] = aml.account_id.id
            res['original_amount'] = amount
            res['unreconciled_amount'] = amount - aml.amount_residual
            res['original_date'] = aml.date
            res['maturity_date'] = aml.date_maturity or aml.date
            res['name'] = aml.name
            res['description'] = aml.move_id.name
            res['ref'] = aml.move_id.ref
            res['amount'] = 0.0
        else:
            res['partner'] = False
            res['account'] = False
            res['amount_original'] = False
            res['amount_unreconciled'] = False
            res['original_date'] = False
            res['maturity_date'] = False
            res['name'] = False
            res['description'] = False
            res['reference'] = False
            res['amount'] = 0.0

        return {'value': res}
        
    def onchange_amount(self, cr, uid , ids, amount, unreconciled_amount, context=None):
        if amount < 0 or amount > unreconciled_amount:
            raise except_osv(_("Error!"),
                             _("Amount should be positive and at most like the unreconciled amount! Please check it"))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
