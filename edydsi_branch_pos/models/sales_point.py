# -*- coding: utf-8 -*-

from openerp import models, fields

class res_sales_point(models.Model):
    _inherit = 'res.sales_point'
    
    pos = fields.Many2one('pos.config', 'POS',
                          ondelete='cascade')

