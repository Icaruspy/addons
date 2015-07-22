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

from openerp.osv import fields
from openerp.osv.osv import Model, TransientModel, except_osv
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round

import openerp.addons.decimal_precision as dp
import time

from openerp import SUPERUSER_ID,api

import logging
_logger = logging.getLogger(__name__)

class account_tax(Model):
    _inherit = 'account.tax'

    _columns = {
        'account_collected_id': fields.property(
            type='many2one',
            relation='account.account',
            string="Invoice Tax Account",
            help="Set the account that will be set by default on invoice tax lines for invoices. Leave empty to use the expense account."),
        'account_paid_id': fields.property(
            type='many2one',
            relation='account.account',
            string="Refund Tax Account",
            help="Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account."),
        'account_analytic_collected_id': fields.property(
            type='many2one',
            relation='account.analytic.account',
            string="Invoice Tax Analytic Account",
            help="Set the analytic account that will be used by default on the invoice tax lines for invoices. Leave empty if you don't want to use an analytic account on the invoice tax lines by default."),
        'account_analytic_paid_id': fields.property(
            type='many2one',
            relation='account.analytic.account',
            string="Refund Tax Analytic Account",
            help="Set the analytic account that will be used by default on the invoice tax lines for refunds. Leave empty if you don't want to use an analytic account on the invoice tax lines by default."),
        'base_code_id': fields.property(
            type='many2one',
            relation='account.tax.code',
            string="Account Base Code",
            help="Use this code for the tax declaration."),
        'tax_code_id': fields.property(
            type='many2one',
            relation='account.tax.code',
            string="Account Tax Code",
            help="Use this code for the tax declaration."),
        'ref_base_code_id': fields.property(
            type='many2one',
            relation='account.tax.code',
            string="Refund Base Code",
            help="Use this code for the tax declaration."),
        'ref_tax_code_id': fields.property(
            type='many2one',
            relation='account.tax.code',
            string="Refund Tax Code",
            help="Use this code for the tax declaration."),

        'company_id': fields.many2one('res.company', 'Company', ondelete="cascade", help="Debug", required=False),
        'country': fields.many2one('res.country', 'Country', ondelete="cascade"),
    }

    _defaults = {
        'company_id': False,
    }

    # Copy and paste of account.py code, extended with context parameter for a more flexible tax structurre
    # It should be directly patched on the original code, but thst will make the module not usable under
    # a standard OpenERP insatallad
    # EXTREME CARE on patches and fixes!! Use under your exclusive responsibability!
    # In theory, standard taxes could be used without changes
    # New taxes can take advantage of a new context paramenter, which are filled with invoice information 
    # from sales and purchase processing
    # User modules could add any extra information. Be carefull in order not to generate regressions
    
    def _applicable(self, cr, uid, taxes, price_unit, product=None, partner=None, context=None):
        res = []
        for tax in taxes:
            if tax.applicable_type=='code':
                localdict = {'price_unit':price_unit, 'product':product, 'partner':partner, 'context':context}
                exec tax.python_applicable in localdict
                if localdict.get('result', False):
                    res.append(tax)
            else:
                res.append(tax)
        return res

    def _unit_compute(self, cr, uid, taxes, price_unit, product=None, partner=None, quantity=0, context=None):
        taxes = self._applicable(cr, uid, taxes, price_unit ,product, partner, context=context)
        res = []
        cur_price_unit=price_unit
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            data = {'id':tax.id,
                    'name':tax.description and tax.description + " - " + tax.name or tax.name,
                    'account_collected_id':tax.account_collected_id.id,
                    'account_paid_id':tax.account_paid_id.id,
                    'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                    'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                    'base_code_id': tax.base_code_id.id,
                    'ref_base_code_id': tax.ref_base_code_id.id,
                    'sequence': tax.sequence,
                    'base_sign': tax.base_sign,
                    'tax_sign': tax.tax_sign,
                    'ref_base_sign': tax.ref_base_sign,
                    'ref_tax_sign': tax.ref_tax_sign,
                    'price_unit': cur_price_unit,
                    'tax_code_id': tax.tax_code_id.id,
                    'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
            if tax.type=='percent':
                amount = cur_price_unit * tax.amount
                data['amount'] = amount

            elif tax.type=='fixed':
                data['amount'] = tax.amount
                data['tax_amount']=quantity
               # data['amount'] = quantity
            elif tax.type=='code':
                localdict = {'price_unit':cur_price_unit, 'product':product, 'partner':partner, 'context':context}
                exec tax.python_compute in localdict
                amount = localdict['result']
                data['amount'] = amount
            elif tax.type=='balance':
                data['amount'] = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)
                data['balance'] = cur_price_unit

            amount2 = data.get('amount', 0.0)
            if tax.child_ids:
                if tax.child_depend:
                    latest = res.pop()
                amount = amount2
                child_tax = self._unit_compute(cr, uid, tax.child_ids, amount, product, partner, quantity, context=context)
                res.extend(child_tax)
                if tax.child_depend:
                    for r in res:
                        for name in ('base','ref_base'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['price_unit'] = latest['price_unit']
                                latest[name+'_code_id'] = False
                        for name in ('tax','ref_tax'):
                            if latest[name+'_code_id'] and latest[name+'_sign'] and not r[name+'_code_id']:
                                r[name+'_code_id'] = latest[name+'_code_id']
                                r[name+'_sign'] = latest[name+'_sign']
                                r['amount'] = data['amount']
                                latest[name+'_code_id'] = False
            if tax.include_base_amount:
                cur_price_unit+=amount2
        return res

    @api.v7
    def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False, context=None):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line

        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        tax_compute_precision = precision
        if taxes and taxes[0].company_id and taxes[0].company_id.tax_calculation_rounding_method == 'round_globally':
            tax_compute_precision += 5
        totalin = totalex = round(price_unit * quantity, precision)
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, product=product, partner=partner, precision=tax_compute_precision, context=context)
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, product=product, partner=partner, precision=tax_compute_precision, context=context)
        for r in tex:
            totalin += r.get('amount', 0.0)
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }
        
    @api.v8
    def compute_all(self, price_unit, quantity, product=None, partner=None, force_excluded=False):
        return self._model.compute_all(
            self._cr, self._uid, self, price_unit, quantity,
            product=product, partner=partner, force_excluded=force_excluded)

    def compute(self, cr, uid, taxes, price_unit, quantity,  product=None, partner=None, context=None):
        _logger.warning("Deprecated, use compute_all(...)['taxes'] instead of compute(...) to manage prices with tax included.")
        return self._compute(cr, uid, taxes, price_unit, quantity, product, partner, context=context)

    def _compute(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, precision=None, context=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute(cr, uid, taxes, price_unit, product, partner, quantity, context=context)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r.get('balance', 0.0) * quantity, precision) - total
            else:
                r['amount'] = round(r.get('amount', 0.0) * quantity, precision)
                total += r['amount']
        return res

    def _unit_compute_inv(self, cr, uid, taxes, price_unit, product=None, partner=None, context=None):
        taxes = self._applicable(cr, uid, taxes, price_unit,  product, partner)
        res = []
        taxes.reverse()
        cur_price_unit = price_unit

        tax_parent_tot = 0.0
        for tax in taxes:
            if (tax.type=='percent') and not tax.include_base_amount:
                tax_parent_tot += tax.amount

        for tax in taxes:
            if (tax.type=='fixed') and not tax.include_base_amount:
                cur_price_unit -= tax.amount

        for tax in taxes:
            if tax.type=='percent':
                if tax.include_base_amount:
                    amount = cur_price_unit - (cur_price_unit / (1 + tax.amount))
                else:
                    amount = (cur_price_unit / (1 + tax_parent_tot)) * tax.amount

            elif tax.type=='fixed':
                amount = tax.amount

            elif tax.type=='code':
                localdict = {'price_unit':cur_price_unit, 'product':product, 'partner':partner, 'context':context}
                exec tax.python_compute_inv in localdict
                amount = localdict['result']
            elif tax.type=='balance':
                amount = cur_price_unit - reduce(lambda x,y: y.get('amount',0.0)+x, res, 0.0)

            if tax.include_base_amount:
                cur_price_unit -= amount
                todo = 0
            else:
                todo = 1
            res.append({
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_collected_id.id,
                'account_paid_id': tax.account_paid_id.id,
                'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'sequence': tax.sequence,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            })
            if tax.child_ids:
                if tax.child_depend:
                    del res[-1]
                    amount = price_unit

            parent_tax = self._unit_compute_inv(cr, uid, tax.child_ids, amount, product, partner, context=context)
            res.extend(parent_tax)

        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['price_unit'] -= total
            r['todo'] = 0
        return res

    def compute_inv(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, precision=None, context=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
        Price Unit is a Tax included price

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        if not precision:
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        res = self._unit_compute_inv(cr, uid, taxes, price_unit, product, partner=None, context=context)
        total = 0.0
        for r in res:
            if r.get('balance',False):
                r['amount'] = round(r['balance'] * quantity, precision) - total
            else:
                r['amount'] = round(r['amount'] * quantity, precision)
                total += r['amount']
        return res

class tax_template(Model):
    _inherit = "account.tax.template"

    def _generate_tax(self, cr, uid, tax_templates, tax_code_template_ref, company_id, context=None):
        """
        This method generate taxes from templates.

        :param tax_templates: list of browse record of the tax templates to process
        :param tax_code_template_ref: Taxcode templates reference.
        :param company_id: id of the company the wizard is running for
        :returns:
            {
            'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
            'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        if context is None:
            context = {}

        tax_obj = self.pool['account.tax']

        res = {}
        todo_dict = {}
        tax_template_to_tax = {}
        for tax in tax_templates:
            vals_tax = {
                'name':tax.name,
                'sequence': tax.sequence,
                'amount': tax.amount,
                'type': tax.type,
                'applicable_type': tax.applicable_type,
                'domain': tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_to_tax) and tax_template_to_tax[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
                'base_code_id': tax.base_code_id and ((tax.base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.base_code_id.id]) or False,
                'tax_code_id': tax.tax_code_id and ((tax.tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.tax_code_id.id]) or False,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_code_id': tax.ref_base_code_id and ((tax.ref_base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_base_code_id.id]) or False,
                'ref_tax_code_id': tax.ref_tax_code_id and ((tax.ref_tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_tax_code_id.id]) or False,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'include_base_amount': tax.include_base_amount,
                'description': tax.description,
                'company_id': False,
                'type_tax_use': tax.type_tax_use,
                'price_include': tax.price_include
            }

            existing_taxes_ids = tax_obj.search(cr, SUPERUSER_ID, [('name','=',tax.name)], context=context)
            if existing_taxes_ids:
                new_tax = existing_taxes_ids[0]
                tax_obj.write(cr, uid, [new_tax], vals_tax, context=context)
            else:
                new_tax = tax_obj.create(cr, uid, vals_tax, context=context)

            tax_template_to_tax[tax.id] = new_tax
            #as the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax] = {
                'account_collected_id': tax.account_collected_id and tax.account_collected_id.id or False,
                'account_paid_id': tax.account_paid_id and tax.account_paid_id.id or False,
            }
        res.update({'tax_template_to_tax': tax_template_to_tax, 'account_dict': todo_dict})
        return res

class res_country(Model):
    _inherit = "res.country"
    
    _columns = {
        'sales_applicable_taxes': fields.many2many('account.tax', 'sales_country_wide_taxes', 'country_id', 'tax_id', 
                                                   'Country wide sales taxes', 
                                                   domain="[('company_id','=',False)]", 
                                                   help="Taxes used for sales, for all companies operating in the country"),
        'payments_applicable_taxes': fields.many2many('account.tax', 'payments_country_wide_taxes', 'country_id', 'tax_id', 
                                                          'Country wide payment taxes', 
                                                          domain="[('company_id','=',False)]", 
                                                          help="Taxes used in payments, for all companies operating in the country"),
    }
    
class res_country_state(Model):
    _inherit = "res.country.state"
    
    _columns = {
        'sales_applicable_taxes': fields.many2many('account.tax', 'sales_state_wide_taxes', 'fed_state_id', 'tax_id', 
                                                   'State wide sales taxes', 
                                                   domain="[('company_id','=',False)]", 
                                                   help="Taxes used for sales, for all companies operating in the country state"),
        'payments_applicable_taxes': fields.many2many('account.tax', 'payments_state_wide_taxes', 'fed_state_id', 'tax_id', 
                                                  'State wide payment taxes', 
                                                   domain="[('company_id','=',False)]", 
                                                   help="Taxes used for payments, for all companies operating in the country state"),
    }
    
class res_company(Model):
    _inherit = "res.company"
    
    _columns = {
        'fiscal_country_state': fields.related('partner_id', 'fiscal_country_state', type="many2one", relation='res.country.state', 
                                         string='Fiscal country', help="Country to be used for fiscal issues"),

        'fiscal_country': fields.related('partner_id', 'fiscal_country_state', 'country_id', type="many2one", relation='res.country', 
                                         readonly=True,
                                         string='Fiscal country', help="Country to be used for fiscal issues"),

        'sales_applicable_taxes': fields.many2many('account.tax', 'sales_company_taxes', 'fed_state_id', 'tax_id', 
                                                   'Company specific sales taxes', 
                                                   domain="[('company_id','=',id)]", 
                                                   help="Taxes used for sales, specific to this company"),
        'payments_applicable_taxes': fields.many2many('account.tax', 'payments_company_taxes', 'fed_state_id', 'tax_id', 
                                                   'Company specific payment taxes', 
                                                   domain="[('company_id','=',id)]", 
                                                   help="Taxes used for payments, specific to this company"),
    }

    def onchange_fiscal_country_state(self, cr, uid, ids, fiscal_country_state_id, context=None):
        cs_obj = self.pool['res.country.state']
        res = {}
        if fiscal_country_state_id:
            cs = cs_obj.browse(cr, uid, fiscal_country_state_id, context=context)
            res['fiscal_country'] = cs.country_id.id
        else:
            res['fiscal_country'] = False

        return {'value': res}

class res_partner(Model):
    _inherit = "res.partner"

    def _get_default_fcs(self, cr, uid, context=None):
        company_obj = self.pool['res.company']
        dc_id = company_obj._company_default_get(cr, uid, 'account.account', context=context)
        if dc_id:
            dc = company_obj.browse(cr, uid, dc_id, context=context)
            return dc.fiscal_country_state and dc.fiscal_country_state.id or False
        else:
            return False

    _columns = {
        'fiscal_country_state': fields.many2one('res.country.state', 'Fiscal country state', help="Country state to be used for fiscal issues"),
        'fiscal_country': fields.related('fiscal_country_state', 'country_id', type="many2one", relation='res.country', 
                                         string='Fiscal country', help="Country to be used for fiscal issues"),
    }

    _defaults = {
        'fiscal_country_state': _get_default_fcs,
    }

    def onchange_fiscal_country_state(self, cr, uid, ids, fiscal_country_state_id, context=None):
        cs_obj = self.pool['res.country.state']
        res = {}
        if fiscal_country_state_id:
            cs = cs_obj.browse(cr, uid, fiscal_country_state_id, context=context)
            res['fiscal_country'] = cs.country_id.id
        else:
            res['fiscal_country'] = False

        return {'value': res}

class wizard_multi_charts_accounts(TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    def _load_template(self, cr, uid, 
                       template_id, company_id, 
                       code_digits=None, obj_wizard=None, 
                       account_ref=None, taxes_ref=None, 
                       tax_code_ref=None, context=None):

        user_obj = self.pool['res.users']
        cu = user_obj.browse(cr, SUPERUSER_ID, uid, context=context)
        current_company = cu.company_id
        cu.write({'company_id': company_id})
        ret = super(wizard_multi_charts_accounts, self)._load_template(cr, uid,
                       template_id, company_id, 
                       code_digits=code_digits, obj_wizard=obj_wizard, 
                       account_ref=account_ref, taxes_ref=taxes_ref, 
                       tax_code_ref=tax_code_ref, context=context)
        cu.write({'company_id': current_company.id})
        return ret


