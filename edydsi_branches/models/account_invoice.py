# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    branch = fields.Many2one('res.branch', 'Branch',
                             readonly=True, states={'draft': [('readonly', False)]},
                             ondelete='restrict')

    sales_point = fields.Many2one('res.sales_point', 'Sales Point',
                                  readonly=True, states={'draft': [('readonly', False)]},
                                  domain="[('usage','=','general')]",
                                  ondelete='restrict')

    @api.onchange('branch')
    def onchange_branch(self):
        for invoice in self:
            invoice.sales_point = invoice.branch.default_sales_point
            
    @api.multi
    def action_number(self):
        sequence_obj = self.pool['ir.sequence']
        for inv in self:
            if inv.type not in ['out_invoice', 'out_refund']:
                continue
            
            if not inv.sales_point or not inv.branch:
                raise except_orm(_('Error'),
                                 _('Invoice should have a defined branch and sales point in order to be validated! Please check it'))

            if not inv.sales_point.legal_id:
                raise except_orm(_('Error'),
                                 _('Sales point should have a defined Legal ID in order to be used! Please check it'))
            if not inv.branch.legal_id:
                raise except_orm(_('Error'),
                                 _('Branch should have a defined Legal ID in order to be used! Please check it'))
            inv.number = "%s-%s-%s" % (inv.branch.legal_id,
                                         inv.sales_point.legal_id,
                                         sequence_obj.next_by_id(self.env.cr, self.env.uid, inv.sales_point.sequence.id,self.env.context))

            super(account_invoice, inv).action_number()
        
        return True


