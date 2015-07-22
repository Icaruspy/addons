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


from openerp import models, fields, api
from openerp.osv.osv import except_osv

from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

class account_bank_printing_model(models.Model):
    _name = 'account.bank_printing_model'
    
    name = fields.Char("Model's name", size=128, required=True)
    notes = fields.Text('Notes')
    report = fields.Many2one('ir.actions.report.xml', 
                             'Current printing model',
                             domain="[('model','=','account.payable_document')]")

class res_bank(models.Model):
    _inherit = "res.bank"
    
    current_printing_model = fields.Many2one('account.bank_printing_model', 
                                             'Current printing model')

class account_payable_document(models.Model):
    _inherit = "account.payable_document"
    
    auto_printed = fields.Boolean('Already printed', default=False)
    _defaults = {
        'name': '********',   
    }

class res_partner_bank(models.Model):
    _inherit = "res.partner.bank"

    auto_cheque_printing = fields.Boolean('Auto cheque writing')
    auto_mask = fields.Char('Mask for numbering generation',
                            help="Use the following expresions in mask for proper number generation\n"
                                 "- %(y4)d for the 4 digits year, %(y2) for 2 digits year (issued date)\n"
                                 "- %(m)d for the month number\n"
                                 "- %(d)d for the day number\n"
                                 "- %(n)d for the number. Normal modifiers, like %(n)08d could be used\n",
                            default="%(n)08d", required=True)

    def action_print_checks(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'
        rpd_obj = self.pool['account.payable_document']
        
        rpb = self.browse(cr, uid, ids[0], context=context)
        
        if not rpb.auto_cheque_printing:
            raise except_osv(_("Error"), 
                             _("This account is not configured for automatic check printing!"))

        if not rpb.bank.current_printing_model:
            raise except_osv(_("Error"), 
                             _("Bank %s has currently no printing model assigned! Please check") % rpb.bank.name)

        to_print = rpd_obj.search(cr, uid, 
                                  [('issuer_account','=',rpb.id), 
                                   ('state','in',['payable']),
                                   ('auto_printed','=',False)],
                                  context=context)

        if len(to_print):
            return {
                'name':_("Print cheques for bank %s") % rpb.name,
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.cheque_writing',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'context': context or {},
            }
        else:
            raise except_osv(_("Warning"), 
                             _("This account has no pending cheque to print!"))

class account_cheque_writing(models.TransientModel):
    _name = 'account.cheque_writing'
    
    first_number = fields.Integer('First number to assign', default=1)
    bank_account = fields.Many2one('res.partner.bank', 'Bank account')
    cheque_count = fields.Integer('# of cheques to print',
                                  compute='getCheques')
   
    @api.depends('bank_account')
    def getCheques(self):
        rpd_obj = self.env['account.payable_document']

        for rec in self:
            cheques = rpd_obj.search([('issuer_account','=',rec.bank_account.id), 
                                      ('auto_printed','=',False)])
            rec.cheque_count = len(cheques)
        
    @api.model
    def default_get(self, fields):
        rpb_obj = self.env['res.partner.bank']
        rpd_obj = self.env['account.payable_document']
        
        res = super(account_cheque_writing, self).default_get(fields)

        active_id = self.env.context['active_id']
        rpb = rpb_obj.browse(active_id)
        
        if 'bank_account' in fields:
            res['bank_account'] = rpb.id
            
        if 'first_number' in fields:
            last_docs = rpd_obj.search([('issuer_account','=',rpb.id),
                                        ('auto_printed','=',True)],
                                       order="number desc",
                                       limit=1)
            if last_docs:
                last_doc = last_docs[0]
                first_number = 1
                try:
                    last_number = last_doc.number
                    first_number = last_number + 1
                except Exception:
                    pass
                res['first_number'] = first_number
                
        return res

    def action_print(self, cr, uid, ids, context=None):
        assert ids and len(ids)==1, 'One at the time'
        
        acw = self.browse(cr, uid, ids[0], context=context)

        today = fields.Date.context_today(acw)
        rpd_obj = self.pool['account.payable_document']

        cheque_ids = rpd_obj.search(cr, uid,
                                 [('issuer_account','=',acw.bank_account.id), 
                                  ('state','in',['payable']),
                                  ('auto_printed','=',False)],
                                 context=context)
        cheques = rpd_obj.browse(cr, uid, cheque_ids, context=context)
        
        if len(cheques):
            # Number assignation
            n = acw.first_number        
            for cheque in cheques:
                cheque.write({
                    'name': cheque.issuer_account.auto_mask % {
                                        'y4': int(cheque.issued_date[0:4]),
                                        'y2': int(cheque.issued_date[2:4]),
                                        'm': int(cheque.issued_date[5:7]),
                                        'd': int(cheque.issued_date[8:10]),
                                        'n': n,
                            },
                    'number': n,
                    'auto_printed': True,
                    'issued_date': today,
                })
                n += 1
    
            report_ids = [ch.id for ch in cheques]
    
            return self.pool['report'].get_action(
                cr, uid, 
                report_ids, 
                acw.bank_account.bank.current_printing_model.report.report_name, 
                context=dict(context, active_model='account.payable_document'),
            )
        else:
            return {'type': 'ir.actions.act_window_close'}
        