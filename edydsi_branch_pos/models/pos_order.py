# -*- coding: utf-8 -*-
"""
Created on Sat Dec 27 10:17:49 2014

@author: dev04_server
"""

from openerp import models, fields, api

class pos_order(models.Model):
    _inherit = "pos.order"

    ticket_reference = fields.Char('Ticket reference')
    ticket_sales_point = fields.Many2one('res.sales_point', 'Ticket Sales Point')

    def _order_fields(self, cr, uid, ui_order, context=None):
        res = super(pos_order, self)._order_fields(cr, uid, ui_order, context=context)
        res['ticket_reference'] = ui_order.get('ticket_reference', False)
        res['ticket_sales_point'] = ui_order.get('ticket_sales_point', False)

        return res
        
    @api.multi
    def write(self, values):
        super(pos_order, self).write(values)
        if 'ticket_reference' in values:
            trs = values['ticket_reference'].split('-')
            if len(trs) == 3:
                seq_number = int(trs[2])
                sequence = self[0].sequence
                if sequence.number_next <= seq_number:
                    sequence.number_next = seq_number + 1
        return True
        
    @api.multi
    def invoice_ref(self):
        res = {}
        for order in self:
            res[order.id] = {'id': order.invoice_id and order.invoice_id.id or 0,
                             'number': order.invoice_id and order.invoice_id.internal_number or ''}
        
        return res
        
