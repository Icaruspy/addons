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

from openerp.osv.osv import Model, TransientModel, except_osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
import openerp.addons.decimal_precision as dp
import time

import logging
_logger = logging.getLogger(__name__)

class account_move_line(Model):
    _inherit = 'account.move.line'
    
    def get_move_reference(self, cr, uid, ids, context=None):
        res = {}
        for aml in self.browse(cr, uid, ids, context=context):
            cr_obj = self.pool['account.customer_reconcile']
            cr_ids = cr_obj.search(cr, uid, [('move','=',aml.move_id.id)])
            name = None
            if cr_ids:
                reconcile = cr_obj.browse(cr, uid, cr_ids[0], context=context)
                name = _("CRECON %s") % reconcile.name
            if not name:
                super_res = super(account_move_line, self).get_move_reference(cr, uid, [aml.id], context=context)
                name = super_res[aml.id]
            res[aml.id] = name
            
        return res

class customer_reconcile(Model):
    '''
    A customer reconcile is the document that associates already made payments with debts of the customer
    '''
    def _get_name(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('default_name', False)

    def _get_journal(self, cr, uid, context=None):
        if context is None: context = {}
        j_id = context.get('default_journal', False)
        if not j_id:
            journal_obj = self.pool['account.journal']
            j_ids = journal_obj.search(cr, uid, [('type','=','sale')], context=context)
            if j_ids and len(j_ids)==1:
                j_id = j_ids[0]
        return j_id

    def _get_narration(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('narration', False)

    def _get_balance(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for crec in self.browse (cr, uid, ids, context=context):
            credits = []
            for credit in crec.credits:
                credits.append({'amount': credit.amount})
            debts = []
            for debt in crec.debts:
                debts.append({'amount': debt.amount})

            res[crec.id] = self._compute_balance (cr, uid, credits, debts)
        return res

    def _compute_balance(self, cr, uid, credit_ids, debt_ids):
        balance = 0.0
        for credit in credit_ids:
            balance += credit['amount']
        for debt in debt_ids:
            balance -= debt['amount']

        return balance

    _name = 'account.customer_reconcile'
    _description = 'Reconciliation of unreciled customer documents'
    _order = "date desc, name desc"
    _columns = {
        'name': fields.char('Reference', 
                            size=256, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'date': fields.date('Date', 
                            readonly=True, 
                            select=True, 
                            states={'draft':[('readonly',False)]}, 
                            help="Efective operation date"),
        'period': fields.many2one('account.period', 'Period', 
                            required=True, readonly=True, 
                            states={'draft':[('readonly',False)]}, 
                            help="Effective date of the reconciliation"),
        'journal': fields.many2one('account.journal', 'Journal', 
                            required=True, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'account': fields.many2one('account.account', 'Account', 
                            required=True, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'credits': fields.one2many('account.customer_reconcile_credit',
                            'crec',
                            'Non reconciled credits', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'debts': fields.one2many('account.customer_reconcile_debt',
                            'crec',
                            'Applied debts', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'notes': fields.text('Notes', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'currency': fields.many2one('res.currency', 
                            string='Moneda', 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'company': fields.many2one('res.company',
                            string='Company', 
                            store=False, 
                            readonly=True,
                            states={'draft':[('readonly',False)]}),
        'state':fields.selection(
            [('draft','Draft'),
             ('posted','Posted'),
             ('canceled','Canceled')
            ], 'State', readonly=True, size=32,
            help=' * \'Draft\' state is used on new document entry. \
                        \n* \'Posted\' is used when the document is registered and account moves are generated \
                        \n* \'Canceled\' is used for canceled documents.'),
        'partner':fields.many2one('res.partner', 'Customer', 
                            change_default=1, 
                            readonly=True, 
                            states={'draft':[('readonly',False)]}),
        'balance': fields.function(_get_balance, method=True, 
                            string='Balance', 
                            type='float', 
                            readonly=True),

        'to_be_checked': fields.boolean('To be checked'),
        'move':fields.many2one('account.move', 
                               'Accounting move', 
                               readonly=True),
        'cancelation_move':fields.many2one('account.move', 
                                      'Cancelation accounting move', 
                                      readonly=True),
    }

    _defaults = {
        'name': '/',
        'journal': _get_journal,
        'state': 'draft',
        'date': fields.date.context_today,
        'company': lambda s,cr,uid,c: s.pool['res.company']._company_default_get(cr, uid, 'account.account', context=c),
    }

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        customer_reconciles = self.browse (cr, uid, ids, context=context)
        return [(crec.id, "%s [%s]" % (crec.name, crec.company_id.name)) for crec in customer_reconciles]

    def onchange_lines(self, cr, uid, ids, 
                        credit_ids, 
                        debt_ids, 
                        context=None):

        credits  = self.resolve_2many_commands(cr, uid, 'credits',  credit_ids,  ['amount'], context=context)
        debits = self.resolve_2many_commands(cr, uid, 'debts', debt_ids, ['amount'], context=context)
        
        return {'value': {'balance': self._compute_balance(cr, uid, credits, debits)}}

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
            res['debt_ids'] = []
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

            domain['journal'] = [('type','=','sale'),('company_id','=',company_id)]
            domain['period']  = [('fiscalyear_id.company_id','=',company_id)]
            domain['account'] = [('company_id','=', company_id)]
        else:
            res['journal'] = False
            res['period'] = False
            res['debt_ids'] = []
            res['account'] = False

            domain['journal'] = [('type','=','sale')]
            domain['period']  = []
            domain['account'] = []

        res['credit_ids'] = []
        res['debt_ids'] = []

        return {'value': res, 'domain': domain}

    def onchange_journal(self, cr, uid, ids, 
                          journal_id, date,
                          context=None):
        res = {}

        if journal_id:
            res['balance']  = 0.0

        res['credit_ids'] = []
        res['debt_ids'] = []

        return {'value': res}

    def onchange_partner(self, cr, uid, ids, 
                            partner_id, 
                            company_id,  
                            period_id,
                            journal_id, 
                            date,
                            context=None):
        return self.onchange_company( cr, uid, ids, 
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

    def action_cancel(self, cr, uid, ids, context=None):
        move_obj = self.pool['account.move']

        for crec in self.browse(cr, uid, ids, context=context):
            val = {
                'state':'canceled',
                'cancelation_move': crec.move and \
                    move_obj.revert(cr, uid, [crec.move.id], 
                                    {'name': crec.name,
                                     'ref': _('CANCELATION'),
                                     'date': fields.date.context_today(self, cr, uid, context=context)}, 
                                     context=context)[crec.move.id] or False, 
            }
            crec.write(val)

        return True

    def action_get_credit_and_debts(self, cr, uid, ids, context=None):
        currency_obj = self.pool['res.currency']
        move_line_obj = self.pool['account.move.line']

        for crec in self.browse(cr, uid, ids, context=context):
            if (not crec.period) or (not crec.company) or (not crec.currency) or (not crec.partner):
                continue

            if crec.state != 'draft':
                continue
                
            company = crec.company
            company_currency = company.currency_id
            period = crec.period

            if period.state != 'draft':
                raise except_osv(_('Error!'), _('Period is not open. Please check it!'))

            domain = self.get_lookup_criteria(cr, uid, [crec.id], 
                                              crec.partner.id, 
                                              crec.company.id, 
                                              period.fiscalyear_id.id, 
                                              context=context)

            for credit in crec.debits:
                credit.unlink()
            for debt in crec.debts:
                debt.unlink()

            ids = move_line_obj.search (cr, uid, domain, context=context)
            raw_moves = move_line_obj.browse(cr, uid, ids, context=context)

            unreconciled = filter(lambda m: not m.reconcile_partial_id, raw_moves)
            reconcile_list = list(set([m.reconcile_partial_id for m in filter(lambda m: m.reconcile_partial_id, raw_moves)]))
            reconciled = [max(r.line_partial_ids, key=lambda m: m.debit or m.credit) for r in reconcile_list]
            
            rds = unreconciled + reconciled

            credits = []
            debits = []

            for rd in rds:
                unreconciled_amount = abs(rd.amount_residual)
                original_amount = rd.debit or rd.credit or 0.0

                if currency_obj.is_zero(cr, uid, company_currency, unreconciled_amount):
                    if rd.reconcile_partial_id:
                        rd.reconcile_partial_id.reconcile_partial_check(context=context)
                    continue

                rs = {
                    'name': rd.move_id.name,
                    'ref': rd.move_id.ref,
                    'move_line': rd.id,
                    'account': rd.account_id.id,
                    'analytic_account': rd.analytic_account_id.id,
                    'original_amount': original_amount,
                    'original_date': rd.date,
                    'due_date': rd.date_maturity or rd.date,
                    'unreconciled_amount': unreconciled_amount,
                    'company': company,
                    'amount': 0.0,
                }

                if rd.credit:
                    rd['amount'] = rd['unreconciled_amount']
                    credits.append(rs)
                elif rd.debit:
                    debits.append(rs)

            credits.sort(key=lambda line: line['due_date'] or line['original_date'])
            debits.sort(key=lambda line: line['due_date'] or line['original_date'])

            crec.write({'credits': [(0, 0, c) for c in credits], 
                        'debits': [(0, 0, d) for d in debits]})

        self.action_reasign_credit(cr, uid, ids, context=context)
        
        return True    

    def action_reasign_credit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for crec in self.browse (cr, uid, ids, context=context):
            if (not crec.period) or (not crec.company) or (not crec.currency) or (not crec.partner):
                continue

            if crec.state != 'draft':
                continue

            total_credit = 0.0
            for credit in crec.cash_entries:
                total_credit += credit.amount

            new_balance = total_credit
            debts = []

            moves = crec.debts
            moves.sort(key=lambda move: move.maturity or move.original_date)
                
            for line in moves:
                amount = min(line.unreconciled_amount, total_credit)
                debts.append((1, line.id, {'amount' : amount}))

                if total_credit > amount:
                    total_credit -= amount
                else:
                    total_credit = 0.0

                new_balance -= amount

            crec.write({'debts': debts})

        return True

    def action_reset_credit_amount(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for crec in self.browse (cr, uid, ids, context=context):
            for line in crec.credits:
                line.write({'amount' : 0.0})

        return True

    def action_reset_debit_amount(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for crec in self.browse (cr, uid, ids, context=context):
            for line in crec.debits:
                line.write({'amount' : 0.0})

        return True

    def get_lookup_criteria(self, cr, uid, ids, 
                            partner_id, company_id, fiscalyear_id, 
                            context=None):
        return [('state','=','valid'), ('move_id.state','=','posted'), ('account_id.type', '=', 'receivable'),
                 ('reconcile_id', '=', False), 
                 ('partner_id', 'child_of', [partner_id]), ('company_id', '=', company_id)]

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] not in ('draft', 'cancel'):
                raise except_osv(_('Error!'), _('Posted documents could not be cancelled!'))
        return super(customer_reconcile, self).unlink(cr, uid, ids, context=context)

    def action_post(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool['account.move']
        move_line_obj = self.pool['account.move.line']
        seq_obj = self.pool['ir.sequence']

        for crec in self.browse(cr, uid, ids, context=context):
            context_multi_currency = context.copy()
            context_multi_currency.update({'date': crec.date})

            if crec.name == '/' or not crec.name:
                name = seq_obj.get(cr, uid, 'customer_voucher') or '/'

            crec.write ({'name': name})
            crec.refresh()

            for credit in crec.credits:
                if credit.amount < 0 or credit.amount > credit.unreconciled_amount:
                    raise except_osv(_('Error !'), 
                                     _('Payment [%s], amount to apply should be positive and not larger than the open amount. Please check it!'),
                                          credit.name)

            for debt in crec.debt_ids:
                if debt.amount < 0 or debt.amount > debt.unreconciled_amount:
                    raise except_osv(_('Error !'), 
                                     _('Debt [%s], amount to apply should be positive and not larger than the open amount. Please check it!'),
                                     debt.name)
                
            #Compute the total amount to be payed
            total_credit = 0.0

            for credit in crec.credits:
                total_credit += credit.amount

            if total_credit == 0:
                raise except_osv(_('Incomplete!'),
                                 _('No payment was selected!'))

            total_debit = 0.0
            applicable_debts = []
            for line in crec.debt_ids:
                if line.amount:
                    applicable_debts.append(line)
                    total_debit += line.amount
                    
            if abs(total_credit - total_debit) >= 0.01:
                raise except_osv(_('Incomplete!'),
                                 _('Balance should be 0 to register the conciliation. Currently: %f!') % (total_credit-total_debit))

            debt_to_apply = list(crec.debits)
            already_applied = 0.0

            move_id = None
            reconcile_lines = []
            ncontext=context.copy()
            ncontext['default_period_id'] = crec.period.id
            ncontext['default_journal_id'] = crec.journal.id

            for credit in crec.uac_ids:

                _logger.debug("Credito %s, amount %f" % (credit.name, credit.amount))
                amount_to_apply = credit.amount

                if amount_to_apply <= 0:
                    continue
                    
                if not move_id:
                    vals = {
                        'name': name,
                        'journal_id': crec.journal.id,
                        'narration': crec.narration,
                        'date': crec.date,
                        'ref': crec.notes,
                        'period_id': crec.period.id,
                    }
                    move_id = move_obj.create(cr, uid, vals, context=ncontext)

                new_line_data = {
                    'move_id': move_id,
                    'account_id': credit.move_line.account_id.id,
                    'partner_id': credit.move_line.partner_id.id,
                    'name': credit.move_line.name,
                    'ref': credit.move_line.ref,
                    'date_maturity': credit.move_line.maturity_date,
                    'debit': amount_to_apply,
                    'credit': 0.0,
                }

                new_line1_id = move_line_obj.create (cr, uid, new_line_data, check=False, context=ncontext)
                reconcile_lines.append([credit.move_line.id, new_line1_id])

                while amount_to_apply and len(debt_to_apply) > 0:
                    #Taking the amount to apply, try to cover as many docs as possible
                    #we check if the receipt line is fully paid or not and create a move line to balance the receipt and initial invoice if needed

                    new_line_data.update({
                        'partner_id': credit.move_line.partner_id.id,
                        'date_maturity': credit.move_line.maturity_date,
                    })
                    
                    debt = debt_to_apply[0]
                    to_apply = min(amount_to_apply, debt.amount - already_applied)
                    
                    _logger.debug("Procesando deuda %s, por aplicar %f, a aplicar en esta deuda %f, ya aplicado %f" % \
                                  (debt.name, amount_to_apply, to_apply, already_applied))

                    if to_apply > 0.0:
                        new_line_data.update({
                            'account_id': debt.move_line.account_id.id,
                            'partner_id': debt.move_line.partner_id.id,
                            'name': debt.move_line.name,
                            'ref': debt.move_line.ref,
                            'date_maturity': debt.move_line.maturity_date,
                            'debit': 0.0,
                            'credit': to_apply,
                        })
                        new_line2_id = move_line_obj.create (cr, uid, new_line_data, check=False, context=ncontext)

                        if debt.move_line_id.partner_id != credit.move_line.partner_id:
                            new_line_data.update({
                                'partner_id': credit.move_line.partner_id.id,
                                'account_id': credit.move_line.account_id.id,
                                'name': _('Transfer'),
                                'debit': to_apply,
                                'credit': 0.0,
                            })
                            new_line3_id = move_line_obj.create (cr, uid, new_line_data, check=False, context=ncontext)

                            new_line_data.update({
                                'partner_id': debt.move_line.partner_id.id,
                                'account_id': debt.move_line.account_id.id,
                                'name': _('Transfer'),
                                'debit': 0.0,
                                'credit': to_apply,
                            })
                            new_line4_id = move_line_obj.create (cr, uid, new_line_data, check=False, context=ncontext)

                            reconcile_lines.append([debt.move_line.id, new_line4_id])
                            reconcile_lines.append([new_line2_id, new_line3_id])
                        else:    
                            reconcile_lines.append([debt.move_line.id, new_line2_id])

                        amount_to_apply -= to_apply
                        already_applied += to_apply
                        
                    if already_applied >= debt.amount:
                        debt_to_apply.pop(0)
                        already_applied = 0.0

            move_obj.post(cr, uid, [move_id], context={})                

            for rec_ids in reconcile_lines:
                if len(rec_ids) >= 2:
                    move_line_obj.reconcile_partial(cr, uid, rec_ids)

            crec.write({'state': 'posted', 'move': move_id})

        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state': 'draft',
            'number': False,
            'move_id': False,
            'credits': False,
            'debts': False,
            'reference': False
        })
        if 'date' not in default:
            default['date'] = fields.date.context_today(self, cr, uid, context=context)
        return super(customer_reconcile, self).copy(cr, uid, id, default, context)

class customer_reconcile_debt(Model):
    _name = 'account.customer_reconcile_debt'
    _description = 'Customer reconcile Debts'
    _order = "due_date,name"

    _columns = {
        'crec': fields.many2one('account.customer_reconcile', 'Customer Reconcile', ondelete='cascade'),
        'name': fields.char('Description', size=256),
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
        'original_date': fields.related('move_line_id','date', 
                                        string="Date", 
                                        type='date', 
                                        readonly=True),
        'maturity_date': fields.related('move_line_id','date_maturity',
                                   string="Maturity date",
                                   type="date",
                                   readonly=True),
        'unreconciled_amount': fields.related('move_line', 'residual',
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
            res['unreconciled_amount'] = amount - aml.residual
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

class customer_reconcile_credit(Model):
    _name = 'account.customer_reconcile_credit'
    _description = 'Customer reconcile credit'
    _order = "due_date,name"

    _columns = {
        'crec': fields.many2one('account.customer_reconcile', 'Customer Reconcile', ondelete='cascade'),
        'name': fields.char('Description', size=256),
        'move_line': fields.many2one('account.move.line', 'Move line', ondelete="restrict"),
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
        'original_amount': fields.related('move_line', 'credit',
                                          string="Original amount",
                                          type="float", digits_compute=dp.get_precision('Account'), 
                                          readonly=True), 
        'original_date': fields.related('move_line_id','date', 
                                        string="Date", 
                                        type='date', 
                                        readonly=True),
        'maturity_date': fields.related('move_line_id','date_maturity',
                                   string="Maturity date",
                                   type="date",
                                   readonly=True),
        'unreconciled_amount': fields.related('move_line', 'residual',
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

            if aml.state != 'posted' or aml.status != 'valid':
                raise except_osv(_("Error!"),
                    _("Move line is not valid or posted! Please check"))

            res['partner'] = aml.partner.ids
            amount = aml.debit or -aml.credit
            res['account'] = aml.account_id.id
            res['original_amount'] = amount
            res['unreconciled_amount'] = amount - aml.residual
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
            res['ref'] = False
            res['amount'] = 0.0

        return {'value': res}

    def onchange_amount(self, cr, uid , ids, amount, unreconciled_amount, context=None):
        if amount < 0 or amount > unreconciled_amount:
            raise except_osv(_("Error!"),
                             _("Amount should be positive and at most like the unreconciled amount! Please check it"))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
