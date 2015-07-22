# -*- coding: utf-8 -*-

from openerp import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class pos_config(models.Model):
    _inherit = 'pos.config'
    
    sales_point = fields.Many2one('res.sales_point',
                                  'Accounting Sales Point',
                                  required=True,
                                  domain="[('usage','=','pos')]",
                                  cascade='restrict')
    branch = fields.Many2one('res.branch',
                             'Branch',
                             required=True,
                             cascade='restrict')
                             
    branch_legal_id = fields.Char('Branch legal ID', 
                                  related='branch.legal_id',
                                  readonly=True,
                                  store=True)
    pos_legal_id = fields.Char('POS legal ID',
                               related='sales_point.legal_id',
                               readonly=True,
                               store=True)
    legal_base = fields.Integer('POS First document',
                                related='sales_point.sequence.number_next',
                                readonly=True)
    timbrado = fields.Char('Timbrado',
                           related='sales_point.timbrado',
                           readonly=True)
    timbrado_due_date = fields.Date('Timbrado due date',
                           related='sales_point.timbrado_due_date',
                           readonly=True)
                           
    anonymous_customer = fields.Many2one('res.partner', 'Anonymous customer', 
                                        help="Customer to use in no name tickets",
                                        required=True)
                             
    @api.onchange('sales_point')
    def onchange_sales_point(self):
        self.sequence_id = self.sales_point.sequence

    @api.multi
    def write(self, vals):
        vals = vals or {}

        super(pos_config, self).write(vals)

        if 'sales_point' in vals:
            for pc in self:
                if pc.sales_point.usage != 'pos':
                    pc.sales_point.usage = 'pos'
                pc.sales_point.pos = pc

        return True
        
        