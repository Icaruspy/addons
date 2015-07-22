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
            cr_obj = self.pool['account.supplier_voucher']
            cr_ids = cr_obj.search(cr, uid, [('move','=',aml.move_id.id), ('cancelation_move','=',aml.move_id.id)])
            name = None
            if cr_ids:
                voucher = cr_obj.browse(cr, uid, cr_ids[0], context=context)
                mask = voucher.move == aml.move_id and _('PAYORDER %s') or _('PAYORDER CANC %s')
                name = mask % voucher.name
            if not name:
                super_res = super(account_move_line, self).get_move_reference(cr, uid, [aml.id], context=context)
                name = super_res[aml.id]
            res[aml.id] = name
            
        return res

class supplier_voucher(Model):
    '''
    A supplier voucher is the document that declares the reception of several values from a partner,
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
                                                  ('type','in',['purchase'])],
                                                 context=context)
                if not journal_ids:
                    journal_ids = journal_obj.search(cr, uid,
                                                     [('company_id','=',default_company_id),
                                                      ('type','in',['pruchase_refund'])],
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
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for cash in sv.cash_entries:
                amount += cash.amount
            res[sv.id] = amount
        return res

    def _get_bt_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for bt in sv.bt_entries:
                amount += bt.amount
            res[sv.id] = amount
        return res

    def _get_csv_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for csv in sv.csv_entries:
                amount += csv.amount
            res[sv.id] = amount
        return res

    def _get_tpdoc_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for doc in sv.tpdoc_entries:
                amount += doc.amount
            res[sv.id] = amount
        return res

    def _get_odoc_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for doc in sv.odoc_entries:
                amount += doc.amount
            res[sv.id] = amount
        return res

    def _get_qm_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for qm in sv.qm_entries:
                amount += qm.amount
            res[sv.id] = amount
        return res

    def _get_debt_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for debt in sv.debt_entries:
                amount += debt.amount
            res[sv.id] = amount
        return res

    def _get_tax_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            amount = 0.0
            for tax in sv.tax_entries:
                amount += tax.tax_amount
            res[sv.id] = amount
        return res

    def _get_balance(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for sv in self.browse (cr, uid, ids, context=context):
            c = []
            for cash in sv.cash_entries:
                c.append({'amount': cash.amount})
            b = []
            for bt in sv.bt_entries:
                b.append({'amount': bt.amount})
            q = []
            for qm in sv.qm_entries:
                q.append({'amount': qm.amount})
            tpd = []
            for doc in sv.tpdoc_entries:
                tpd.append({'amount': doc.amount})
            od = []
            for doc in sv.odoc_entries:
                od.append({'amount': doc.amount})
            db = []
            for debt in sv.debt_entries:
                db.append({'amount': debt.amount})
            tx = []
            for tax in sv.tax_entries:
                db.append({'amount': tax.tax_amount})

            res[sv.id] = self._compute_balance (cr, uid, c, b, q, tpd, od, db, tx)
        return res

    def _compute_balance(self, cr, uid, 
                            cash_entry_ids, 
                            bt_entry_ids, 
                            qm_entry_ids, 
                            tpdoc_entry_ids, 
                            odoc_entry_ids, 
                            debt_entry_ids,
                            tax_entry_ids,
                            context=None):
        balance = 0.0
        for cash in cash_entry_ids:
            balance += cash['amount']
        for bt in bt_entry_ids:
            balance += bt['amount']
        for qm in qm_entry_ids:
            balance += qm['amount']
        for tpdoc in tpdoc_entry_ids:
            balance += tpdoc['amount']
        for odoc in odoc_entry_ids:
            balance += odoc['amount']
        for debt in debt_entry_ids:
            balance -= debt['amount']
        for tax in tax_entry_ids:
            balance += tax['tax_amount']

        return balance

    _name = 'account.supplier_voucher'
    _description = 'supplier vouchers'
    _order = "date desc, id desc"
    _columns = {
        'name': fields.char('Reference', 
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
             ('ready','Ready to post'),
             ('posted','Posted'),
             ('payed','Payed'),
             ('canceled','Canceled')
            ], 'State', readonly=True, size=32,
            help=' * \'Draft\' state is used on new document entries. \
                        \n* \'Ready to post\' when all data is loaded and the document is ready for approval \
                        \n* \'Posted\' is used when the document is registered and account moves are generated \
                        \n* \'Payed\' is used when the supplier has already recognized the payment \
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
                            readonly=True, 
                            states={'draft':[('readonly',False)]}, 
                            help="Acumulated payments, registered but not assigned to any document"),
        'to_be_checked': fields.boolean('To be checked'),
        'move': fields.many2one('account.move', 
                                'Account move', 
                                readonly=True),

        'amount_to_pay': fields.float('Amount to pay', 
                                      digits_compute=dp.get_precision('Account'),
                                      readonly=True, 
                                      states={'draft':[('readonly',False)]}, 
                                      help="Amount you wish to pay with this payment order"),

        'cancelation_move': fields.many2one('account.move', 
                                            'Cancelation accounting move', 
                                            readonly=True),
                                            
        'received_by': fields.char('Received by', size=128,
                            readonly=True, 
                            states={'posted':[('readonly',False)]}, 
                            help="Name of the supplier's person accepting the payment"),
        'received_on': fields.date('Received on',
                            readonly=True, 
                            states={'posted':[('readonly',False)]}, 
                            help="Date of the effective reception by supplier"),
        'reception_notes': fields.text('Reception notes',
                            readonly=True, 
                            states={'posted':[('readonly',False)], 'payed':[('readonly',False)]}),

        'partner': fields.many2one('res.partner', 
                            'Supplier', 
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
        'qm_total': fields.function(_get_qm_total, 
                            method=True, 
                            string='Total retentions', 
                            type='float', 
                            readonly=True),
        'tpdoc_total': fields.function(_get_tpdoc_total, 
                            method=True, 
                            string='Total third party documents', 
                            type='float', 
                            readonly=True),
        'odoc_total': fields.function(_get_odoc_total, 
                            method=True, 
                            string='Total own documents', 
                            type='float', 
                            readonly=True),
        'debt_total': fields.function(_get_debt_total, 
                            method=True, 
                            string='Total debts', 
                            type='float', 
                            readonly=True),

        'tax_total': fields.function(_get_debt_total, 
                            method=True, 
                            string='Total taxes', 
                            type='float', 
                            readonly=True),

        'cash_entries':fields.one2many('account.sv_cash',
                            'sv',
                            'Cash', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'bt_entries':fields.one2many('account.sv_bank_transfer',
                            'sv',
                            'Bank transfers', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'qm_entries':fields.one2many('account.sv_quick_move',
                            'sv',
                            'Performed retentions', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'tpdoc_entries':fields.one2many('account.sv_tpdoc',
                            'sv',
                            'Third party documents', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'odoc_entries':fields.one2many('account.sv_odoc',
                            'sv',
                            'Own documents', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'debt_entries':fields.one2many('account.sv_debt',
                            'sv',
                            'Applied debts', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'tax_entries':fields.one2many('account.sv_tax',
                            'sv',
                            'Applied taxes', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
    }

    _defaults = {
        'name': _get_name,
        'journal':_get_journal,
        'reference': _get_reference,
        'state': 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        svs = self.browse (cr, SUPERUSER_ID, ids, context=context)
        return [(sv.id, "%s [%s]" % (sv.name or 'Draft', sv.company.name)) for sv in svs]

    def onchange_lines(self, cr, uid, ids, 
                            cash_entry_ids, 
                            bt_entry_ids, 
                            qm_entry_ids, 
                            tpdoc_entry_ids, 
                            odoc_entry_ids, 
                            debt_entry_ids,
                            tax_entry_ids,
                            context=None):

        c  = self.resolve_2many_commands(cr, uid, 'cash_entries', cash_entry_ids, ['amount'], context=context)
        b  = self.resolve_2many_commands(cr, uid, 'bt_entries',   bt_entry_ids,   ['amount'], context=context)
        q  = self.resolve_2many_commands(cr, uid, 'qm_entries',   qm_entry_ids,   ['amount'], context=context)
        tpd  = self.resolve_2many_commands(cr, uid, 'tpdoc_entries',  tpdoc_entry_ids,  ['amount'], context=context)
        od  = self.resolve_2many_commands(cr, uid, 'odoc_entries',  odoc_entry_ids,  ['amount'], context=context)
        db = self.resolve_2many_commands(cr, uid, 'debt_entries', debt_entry_ids, ['amount'], context=context)
        tx = self.resolve_2many_commands(cr, uid, 'tax_entries', debt_entry_ids, ['tax_amount'], context=context)

        return {'value': {'balance': self._compute_balance(cr, uid, c, b, q, tpd, od, db, tx)}}

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
                                        [('company_id','=',company_id),('type','=','purchase')],
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

            domain['journal'] = [('type','in',['purchase']), ('company_id','=',company_id)]
            domain['period']  = [('fiscalyear_id.company_id','=',company_id)]
            domain['account'] = [('company_id','=', company_id)]
        else:
            res['journal'] = False
            res['period'] = False
            res['debt_entries'] = []
            res['account'] = False

            domain['journal'] = [('type','in',['purchase'])]
            domain['period']  = []
            domain['account'] = []

        res['cash_ids'] = []
        res['bt_ids'] = []
        res['csv_ids'] = []
        res['qm_ids'] = []
        res['doc_ids'] = []
        res['debt_ids'] = []
        res['cash_total'] = 0.0
        res['bt_total'] = 0.0
        res['csv_total'] = 0.0
        res['qm_total'] = 0.0
        res['doc_total'] = 0.0
        res['debt_total'] = 0.0
        res['tax_total'] = 0.0

        return {'value': res, 'domain': domain}

    def onchange_journal(self, cr, uid, ids, 
                          journal_id, date,
                          context=None):
        res = {}
        if journal_id:
            res['balance']  = 0.0

        res['cash_ids'] = []
        res['bt_ids'] = []
        res['csv_ids'] = []
        res['qm_ids'] = []
        res['doc_ids'] = []
        res['debt_ids'] = []
        res['cash_total'] = 0.0
        res['bt_total'] = 0.0
        res['qm_total'] = 0.0
        res['tpdoc_total'] = 0.0
        res['odoc_total'] = 0.0
        res['debt_total'] = 0.0

        return {'value': res}

    def onchange_partner(self, cr, uid, ids, 
                            partner_id, 
                            company_id,  
                            period_id,
                            journal_id, 
                            date,
                            context=None):
        occ = self.onchange_company(cr, uid, ids, 
                            company_id, journal_id, partner_id, period_id, date,
                            context=context)
        return occ

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
        return [('state','=','valid'), ('move_id.state','=','posted'), ('account_id.type', '=', 'payable'),
                 ('reconcile_id', '=', False), 
                 ('partner_id', 'child_of', [partner_id]), 
                 ('company_id', '=', company_id)]

    def action_print(self,cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        return self.pool['report'].get_action(cr, uid, ids, 'supplier_voucher_print', context=context)

    def action_get_debts(self, cr, uid, ids, context=None):
        currency_obj = self.pool['res.currency']
        move_line_obj = self.pool['account.move.line']

        for sv in self.browse(cr, uid, ids, context=context):
            if (not sv.period) or (not sv.company) or (not sv.currency) or (not sv.partner):
                continue

            if sv.state != 'draft':
                continue
                
            company = sv.company
            company_currency = company.currency_id
            period = sv.period

            if period.state != 'draft':
                raise except_osv(_('Error!'), _('Period is not open. Please check it!'))

            domain = self.get_lookup_criteria(cr, uid, [sv.id], 
                                              sv.partner.id, 
                                              sv.company.id, 
                                              period.fiscalyear_id.id, 
                                              context=context)

            for debt in sv.debt_entries:
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
            total_to_pay = 0.0
            for line in moves:
                if line.debit:
                    unassigned_credit += line.amount_residual
                    continue
                    
                amount_unreconciled = abs(line.amount_residual)
                total_to_pay += amount_unreconciled

                if currency_obj.is_zero(cr, uid, company_currency, amount_unreconciled):
                    if line.reconcile_partial_id:
                        line.reconcile_partial_id.reconcile_partial_check(context=context)
                    continue

                rs = {
                    'sv': sv.id,
                    'move_line':line.id,
                    'amount' : 0.0,
                }
                debts.append((0, 0, rs))

            if debts or unassigned_credit:
                sv.write({
                    'unassigned_payments' : unassigned_credit,
                    'debt_entries': debts,
                    'amount_to_pay': total_to_pay})
                sv.action_compute_retentions()

        return True
        
    def action_compute_retentions(self, cr, uid, ids, context=None):
        context = context or {}
        sv_tax_obj = self.pool['account.sv_tax']

        for sv in self.browse(cr, uid, ids, context=context):
            if (not sv.period) or (not sv.company) or (not sv.currency) or (not sv.partner):
                continue

            if sv.state != 'draft':
                continue
            
            company = sv.company
            tax_list = company.payments_applicable_taxes

            cstates = set()
            countries = set()
            
            if company.fiscal_country_state:
                cstates.add(company.fiscal_country_state)
            if company.fiscal_country:
                countries.add(company.fiscal_country)
            if sv.partner.fiscal_country_state:
                cstates.add(sv.partner.fiscal_country_state)
            if sv.partner.fiscal_country:
                cstates.add(sv.partner.fiscal_country_state)
    
            for cstate in cstates:
                tax_list += cstate.payments_applicable_taxes
            for country in countries:
                tax_list += country.payments_applicable_taxes            

            # Remove old automatic entries            
            for sv_tax in sv.tax_entries:
                if sv_tax.automatic:
                    sv_tax.unlink()

            taxes_to_consider = []
            for addtax in tax_list:
                oct = sv_tax_obj.onchange_tax(cr, uid, [], addtax.id, sv.id, sv.company.id, sv.currency.id, sv.parnter.id, context=context)
                
                vals = oct['value']
                vals['automatic'] = True
                taxes_to_consider.append((0, 0, vals))                

            if taxes_to_consider:
                sv.write({'tax_entries': taxes_to_consider})
    
        return True

    def action_reasign_credit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for sv in self.browse(cr, uid, ids, context=context):
            if (not sv.period) or (not sv.company) or (not sv.currency) or (not sv.partner):
                continue

            if sv.state != 'draft':
                continue

            total_credit = 0.0
            for cash in sv.cash_entries:
                total_credit += cash.amount
            for bt in sv.bt_entries:
                total_credit += bt.amount
            for qm in sv.qm_entries:
                total_credit += qm.amount
            for tpdoc in sv.tpdoc_entries:
                total_credit += tpdoc.amount
            for odoc in sv.odoc_entries:
                total_credit += odoc.amount
            for tax in sv.tax_entries:
                total_credit += tax.amount

            new_balance = total_credit
            debts = []
            moves = list(sv.debt_entries)
            moves.sort(key=lambda move: move.maturity_date or move.original_date)
                
            for line in moves:
                amount = min(line.unreconciled_amount, total_credit)
                debts.append((1, line.id, {'amount' : amount}))

                if total_credit > amount:
                    total_credit -= amount
                else:
                    total_credit = 0.0

                new_balance -= amount

            sv.write({'debt_entries': debts})

        return True

    def action_reset_amount(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for sv in self.browse (cr, uid, ids, context=context):
            for line in sv.debt_entries:
                line.write({'amount' : 0.0})

        return True

    def action_ready_to_approve(self, cr, uid, ids, context=None):
        sequence_obj = self.pool['ir.sequence']

        for sv in self.browse(cr, uid, ids, context=context):
            if sv.state != 'draft':
                raise except_osv(_('Error!'), 
                      _('Only vouchers in "Draft" state could be set ready to approve!'))
            name = sequence_obj.get(cr, uid, 'payment_order') or '/'

            sv.write({'name':name, 'state': 'ready'})

        return True            
        
    def action_back_to_draft(self, cr, uid, ids, context=None):
        for sv in self.browse(cr, uid, ids, context=context):
            if sv.state != 'ready':
                raise except_osv(_('Error!'), 
                      _('Only vouchers in "Ready to approve" state could be moved back to draft!'))
            sv.write({'state': 'draft'})

        return True
        
    def action_payment_recognized(self, cr, uid, ids, context=None):
        for sv in self.browse(cr, uid, ids, context=context):
            if sv.state != 'posted':
                raise except_osv(_('Error!'), 
                      _('Only vouchers already issued could be considered payed!'))

            if not sv.received_by or not sv.received_on:
                raise except_osv(_('Error!'), 
                      _('Please fill both, received by and reception date before setting the payment order as payed!'))

            sv.write({'state': 'payed'})

        return True            

    def action_cancel(self, cr, uid, ids, context=None):
        move_obj = self.pool['account.move']

        for sv in self.browse(cr, uid, ids, context=context):
            if sv.state not in ['posted','payed']:
                continue
            val = {
                'state':'canceled',
                'cancel_move': sv.move and \
                    move_obj.revert(cr, uid, [sv.move.id], 
                                    {'name': sv.name,
                                     'ref': _('CANCELATION'),
                                     'date': fields.date.context_today(self, cr, uid, context=context)}, 
                                     context=context)[sv.move.id] or False, 
            }
            sv.write(val)

        return True

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] in ['posted', 'canceled']:
                raise except_osv(_('Error!'), 
                      _('Posted or canceled vouchers could not be deleted!'))
        return super(supplier_voucher, self).unlink(cr, uid, ids, context=context)

    def action_post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool['account.move']
        move_line_obj = self.pool['account.move.line']
        user_obj = self.pool['res.users']

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
                'debit': 0.0,
                'credit': amount_to_apply,
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
                        'debit': to_apply,
                        'credit': 0.0,
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
                            'debit': 0.0,
                            'credit': to_apply,
                        })
                        new_line3_id = move_line_obj.create (cr, uid, 
                                                    move_line, check=False, 
                                                    context=ncontext)

                        move_line.update({
                            'partner_id': debt.move_line.partner_id.id,
                            'account_id': debt.move_line.account_id.id,
                            'debit': to_apply,
                            'credit': 0.0,
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
                    'debit': amount_to_apply,
                    'credit': 0.0,
                }

                move_line_obj.create(cr, uid, move_line, check=False, context=ncontext)

            return already_applied, move_1

        user = user_obj.browse(cr, uid, uid, context=context)
        saved_company = user.company_id

        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.move:
                continue

            user.write({'company_id': voucher.company.id})

            context_multi_currency = context.copy()
            context_multi_currency.update({'date': voucher.date})

            #Compute the total amount to be payed
            total_credit = 0.0

            for cash in voucher.cash_entries:
                total_credit += cash.amount

            for bt in voucher.bt_entries:
                total_credit += bt.amount

            for qm in voucher.qm_entries:
                total_credit += qm.amount

            for tpdoc in voucher.tpdoc_entries:
                total_credit += tpdoc.amount
                if tpdoc.doc.state != 'data_complete':
                    raise except_osv(_('Error !'), 
                                     _('Third party document [%s] is not longer in data complete state!. Please check it!') % \
                                     tpdoc.doc.name)

            for odoc in voucher.odoc_entries:
                total_credit += odoc.amount

            for debt in voucher.debt_entries:
                if debt.amount < 0 or debt.amount > debt.unreconciled_amount:
                    raise except_osv(_('Error !'), 
                                     _('Debt [%s], amount to apply should be positive and not larger than the open amount. Please check it!') % \
                                     debt.name)

            if total_credit == 0:
                    raise except_osv(_('Not complete!'),
                        _('No credit entered!'))

            move = {
                'name': voucher.name,
                'ref': voucher.reference,
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
                             voucher.journal.default_debit_account_id, 
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

            #Process third party documents
                
            for tpdoc in voucher.tpdoc_entries:
                _logger.debug("Document %s, amount %f" % (tpdoc.doc.name, tpdoc.amount))

                already_applied, aml_id = \
                process_debt(tpdoc.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             "%s-%s" % (tpdoc.doc.issuer_account.bank_name, tpdoc.doc.name), 
                             voucher.partner, 
                             tpdoc.credit_account, 
                             move_id,
                             tpdoc.currency,
                             tpdoc.original_amount,
                             tpdoc.maturity_date,
                             False,
                             False)

                tpdoc.doc.passed_to(voucher.partner.id)
                
            #Process own documents
            pdoc_obj = self.pool['account.payable_document']
            
            for odoc in voucher.odoc_entries:
                _logger.debug("Document %s, amount %f" % (odoc.doc.name, odoc.amount))

                vals = pdoc_obj.default_get(cr, uid,
                                            pdoc_obj.fields_get(cr, uid, context=context),
                                            context=context)                
                vals.update({
                    'doc_type': 'cheque',
                    'issuer_account': odoc.bank_account.id,
                    'original_amount': odoc.original_amount,
                    'amount': odoc.amount,
                    'currency': odoc.currency.id,
                    'maturity_date': odoc.maturity_date,
                    'transferable': odoc.transferable,
                    'issuer_account': odoc.bank_account.id,
                    'company': voucher.company.id,
                })
                newOdocId = pdoc_obj.create(cr, uid, vals, context=context)
                odoc.write({'doc': newOdocId})
                odoc.doc.complete()
                odoc.refresh()                
                
                already_applied, aml_id = \
                process_debt(odoc.amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             "%s-%s" % (odoc.doc.issuer_account.bank_name, odoc.doc.issuer_account.name), 
                             voucher.partner, 
                             voucher.account, 
                             move_id,
                             odoc.currency,
                             odoc.original_amount,
                             voucher.date,
                             False,
                             False)

                odoc.doc.pay(voucher.partner.id, voucher.account.id, voucher.date, context=context)
                
            #Process taxes
                
            for tax in voucher.tax_entries:
                _logger.debug("Tax %s, amount %f" % (tax.name, tax.tax_amount))

                already_applied, aml_id = \
                process_debt(tax.tax_amount, 
                             already_applied, 
                             voucher,
                             applicable_debts,  
                             "%s" % tax.name, 
                             voucher.partner, 
                             tax.account, 
                             move_id,
                             voucher.currency,
                             0.0,
                             voucher.date,
                             False,
                             False)

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
        return super(supplier_voucher, self).copy(cr, uid, id, default, context)

class sv_cash(Model):
    _name = 'account.sv_cash'
    _description = 'Received cash'

    def _get_currency(self, cr, uid, context=None):
        if not context: context = {}
        return context.get('default_currency', False)

    _columns = {
        'sv':fields.many2one('account.supplier_voucher', 'supplier voucher', ondelete='cascade'),
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
        return super (sv_cash, self).create (cr, uid, vals, context=context)

    def write (self, cr, uid, ids, vals, context=None):
        vals = vals or {}
        if 'original_amount' in vals or 'exchange_rate' in vals:
            vals['exchange_rate'] = vals['original_amount'] * vals['exchange_rate']
        return super (sv_cash, self).write (cr, uid, ids, vals, context=context)

    def onchange_currency (self, cr, uid, ids, currency_id, original_amount, sv_currency_id, context=None):
        if not context: context={}
        
        if not sv_currency_id:
            raise except_osv(_("Error!"),
                _("No currency defined. Probably you didn't select the company yet! Please check"))
                
        if not currency_id:
            return False
            
        currency_obj = self.pool['res.currency']
        from_currency = currency_obj.browse (cr, uid, currency_id, context=context)
        to_currency = currency_obj.browse (cr, uid, sv_currency_id, context=context)
        return {'value': {
                    'exchange_rate': currency_obj._get_conversion_rate (
                                        cr, uid, from_currency, to_currency, 
                                        context=context),
                    'amount': currency_obj.compute (
                                        cr, uid, currency_id, sv_currency_id, original_amount, 
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

class sv_bt(Model):
    _name = 'account.sv_bank_transfer'
    _description = 'Received bank transfer'

    def _get_currency (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('default_currency', False)

    def _get_transfer_date (self, cr, uid, context=None):
        if not context: context = {}
        return context.get('transfer_date', fields.date.context_today(self, cr, uid, context=context))

    _columns = {
        'sv':fields.many2one('account.supplier_voucher', 'supplier voucher', ondelete='cascade'),
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
        return super (sv_bt, self).create (cr, uid, vals, context=context)

    def write (self, cr, uid, ids, vals, context=None):
        vals['amount'] = vals.get('original_amount', 0.0) * vals.get('exchange_rate', 0.0)
        return super (sv_bt, self).write (cr, uid, ids, vals, context=context)
        
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
                              currency_id, original_amount, sv_currency_id, 
                              context=None):
        if not context: context={}

        if not sv_currency_id:
            raise except_osv(_("Error!"),
                _("No currency defined. Probably you didn't select the company yet! Please check"))
                
        if not currency_id:
            return
            
        currency_obj = self.pool['res.currency']
        from_currency = currency_obj.browse (cr, uid, currency_id, context=context)
        if sv_currency_id:
            to_currency = currency_obj.browse (cr, uid, sv_currency_id, context=context)
            return {'value': {
                        'exchange_rate': currency_obj._get_conversion_rate (
                                            cr, uid, from_currency, to_currency, 
                                            context=context),
                        'amount': currency_obj.compute (
                                            cr, uid, currency_id, sv_currency_id, original_amount, 
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

class sv_qm(Model):
    _name = 'account.sv_quick_move'
    _description = 'Document receipt Retentions'
    _order = "description"

    _columns = {
        'sv':fields.many2one('account.supplier_voucher', 'supplier Voucher', ondelete='cascade'),
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

class sv_tpdoc(Model):
    _name = 'account.sv_tpdoc'
    _description = 'supplier voucher third party document'
    _order = "description"

    _columns = {
        'sv':fields.many2one('account.supplier_voucher', 'supplier voucher', ondelete='cascade'),
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

class sv_odoc(Model):
    _name = 'account.sv_odoc'
    _description = 'supplier voucher own document'
    _order = "description"

    def _get_default_currency(self, cr, uid, context=None):
        user_obj = self.pool['res.users']
        
        user = user_obj.browse(cr, uid, uid, context=context)
        return user.company_id.currency_id.id
        
    def _get_default_bank_account(self, cr, uid, context=None):
        user_obj = self.pool['res.users']
        rpb_obj = self.pool['res.partner.bank']
        
        user = user_obj.browse(cr, uid, uid, context=context)

        rpb_ids = rpb_obj.search(cr, uid, 
                                 [('partner_id','=',user.company_id.partner_id.id)], 
                                 context=context)
        return rpb_ids and rpb_ids[0] or False
        
    _columns = {
        'sv':fields.many2one('account.supplier_voucher', 'supplier voucher', ondelete='cascade'),
        'doc':fields.many2one('account.payable_document', 'Payable Document', readonly=True),
        'original_amount': fields.float('Original amount'),
        'currency': fields.many2one('res.currency', 'Currency', required=True),
        'maturity_date': fields.date('Maturity date', required=True), 
        'exchange_rate': fields.float('Exchange rate', digits=(8,3)),
        'transferable': fields.boolean('Transferable?'),
        'bank_account': fields.many2one('res.partner.bank', 'Bank account', required=True),
        'credit_account':fields.many2one('account.account', 'Credit account', required=True),
        'analytic_account':fields.many2one('account.analytic.account', 'Analitic account'),
        'description':fields.char('Description', size=256),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
    }
    
    _defaults = {
        'maturity_date': fields.date.context_today,
        'currency': _get_default_currency,
        'transferable': True,
        'bank_account': _get_default_bank_account,
    }

    def onchange_oamount(self, cr, uid, ids, original_amount, exchange_rate, context=None):
        return {'value': {
            'amount': original_amount * exchange_rate,        
        }}

    def onchange_currency(self, cr, uid, ids, currency_id, original_amount, payment_currency_id, context=None):
        if not currency_id or not payment_currency_id:
            return False

        currency_obj = self.pool['res.currency']
        
        to_currency = currency_obj.browse (cr, uid, payment_currency_id, context=context)
        from_currency = currency_obj.browse(cr, uid, currency_id, context=context)
        return {'value': {
                    'exchange_rate': currency_obj._get_conversion_rate (
                                        cr, uid, from_currency, to_currency, 
                                        context=context),
                    'amount': currency_obj.compute (
                                        cr, uid, from_currency.id, to_currency.id, original_amount, 
                                        context=context),
                }}
        
    def onchange_transferable (self, cr, uid, ids, transferable, company_id, context=None):
        if not context: context = {}

        if not company_id:
            return False

        company_obj = self.pool['res.company']

        company = company_obj.browse(cr, uid, company_id, context=context)

        tdoc_account = company.t_pdocs_account
        if not tdoc_account:
            raise except_osv(_("Configuration error!"),
                _("No account defined on [Account for payable documents] for company %s!") % company.name)
        
        ntdoc_account = company.nt_pdocs_account
        if not ntdoc_account:
            raise except_osv(_("Configuration error!"),
                _("No account defined on [Account for not transferable payable documents] for company %s!") % company.name)

        if transferable:
            account = tdoc_account
        else:
            account = ntdoc_account

        res = {'value': {
                 'credit_account': account.id,
              }}

        return res

class sv_tax(Model):
    _name = 'account.sv_tax'
    _description = 'Payment taxes'
    _order = "sequence"

    _columns = {
        'sequence': fields.integer('Sequence', required=True),
        'sv': fields.many2one('account.supplier_voucher', 'supplier voucher', ondelete='cascade'),
        'tax': fields.many2one('account.tax', 'Tax to apply', 
                               required=True,
                               ondelete='restrict'),
        'name': fields.related('tax', 'name',
                               string='Tax Name', 
                               readonly=True,
                               size=64),
        'base': fields.float('Base', required=True, digits=(16,2), help="Base of tax computation."),
        'base_amount': fields.float('Base Amount', required=True, digits=(16,2), help="Base of tax computation, in company currency"),
        'amount': fields.float('Tax', required=True, digits=(16,2)),
        'tax_amount': fields.float('Tax Amount', required=True, digits=(16,2), help="Base of tax computation, in company currency"),
        'base_code_id': fields.related('tax','base_code_id',
                                       string='Account Base Code',
                                       type="many2one", relation='account.tax.code', 
                                       help="Use this code for the tax declaration.",
                                       readonly=True),
        'tax_code_id': fields.related('tax','tax_code_id',
                                       string='Account Tax Code',
                                       type="many2one", relation='account.tax.code', 
                                       help="Use this code for the tax declaration.",
                                       readonly=True),
        'account': fields.many2one('account.account', 'Tax Account'),
        'automatic': fields.boolean('Automatically computed?', readonly=True),
    }
    
    _defaults = {
        'automatic': False,    
    }
        
    def onchange_tax(self, cr, uid, ids, tax_id, date, code, company_id, currency_id, supplier_id, context=None):
        if tax_id and ids:
            tax_obj = self.pool['account.tax']
            cur_obj = self.pool['res.currency']
            company_obj = self.pool['res.company']
            partner_obj = self.pool['res.partner']

            assert len(ids)==1, 'One at the time'
            
            sv_tax = self.browse(cr, uid, ids, context=context)
            
            tax_to_add = tax_obj.browse(cr, uid, tax_id, context=context)
            company_currency = cur_obj.browse(cr, uid, currency_id, context=context)
            company = company_obj.browse(cr, uid, company_id, context=context)
            supplier = partner_obj.browse(cr, uid, supplier_id, context=context)
            
            effective_date = date or fields.date.context_today(self, cr, uid, context=context)
            tax_context = {
                'pool': self.pool,
                'uid': uid,
                'date': effective_date,
                'code': code,
                'company': company,
                'currency': company_currency,
                'supplier': supplier,
            }

            # Add new automatic entries                    
            val = {}
            val['base'] = sv_tax.sv.amount_to_pay
            val['amount'] = 0.0
            val['base_amount'] = 0.0 
            val['tax_amount'] = 0.0
            
            for tax in tax_to_add.compute_all(sv_tax.sv.amount_to_pay, 1.00, 
                                              None,
                                              tax_context, 
                                              supplier)['taxes']:
                if not val:
                    val['name'] = tax['name']
                    val['sequence'] = tax['sequence']
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['account'] = tax['account_collected_id']
                    
                val['tax'] += tax['amount']

                val['base_amount'] += cur_obj.compute(cr, uid, sv_tax.sv.currency.id, 
                                                     company_currency.id, val['base'] * tax['base_sign'], 
                                                     context={'date': effective_date}, 
                                                     round=False)
                val['tax_amount'] += cur_obj.compute(cr, uid, sv_tax.sv.currency.id, 
                                                    company_currency.id, val['tax'] * tax['tax_sign'], 
                                                    context={'date': effective_date}, 
                                                    round=False)

            return {'value': val}            
        else:
            return False            
        
class sv_debt(Model):
    _name = 'account.sv_debt'
    _description = 'supplier voucher Debts'
    _order = "maturity_date"

    _columns = {
        'sv': fields.many2one('account.supplier_voucher', 'supplier voucher', ondelete='cascade'),
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
                                 string="supplier",
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
        return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
