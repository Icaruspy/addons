#-*- coding:utf-8 -*-
import os
import openerp
from openerp.osv import osv, fields
from openerp import tools, models, api, _
from openerp.exceptions import Warning
from datetime import datetime, date
from openerp.tools.translate import _


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.one
    def action_wait(self):
	if self.sale_order_aprobe == False:
        	self.check_limit()
        return super(sale_order, self).action_wait()

    @api.one
    def check_limit(self):
        if self.order_policy == 'prepaid':
            return True

        # We sum from all the sale orders that are aproved, the sale order
        # lines that are not yet invoiced
        domain = [('order_id.partner_id', '=', self.partner_id.id),
                  ('invoiced', '=', False),
                  ('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
        order_lines = self.env['sale.order.line'].search(domain)
        none_invoiced_amount = sum([x.price_subtotal for x in order_lines])

        # We sum from all the invoices that are in draft the total amount
        domain = [
            ('partner_id', '=', self.partner_id.id), ('state', '=', 'draft')]
        draft_invoices = self.env['account.invoice'].search(domain)
        draft_invoices_amount = sum([x.amount_total for x in draft_invoices])

        available_credit = self.partner_id.credit_limit + (self.partner_id.credit_limit*0.05)- \
            self.partner_id.credit - \
            none_invoiced_amount - draft_invoices_amount

        if self.amount_total > available_credit:
            msg = 'No se puede confirmar el Pedido ya que el cliente no tiene credito suficiente.\
                    Puede pasar la politica de facturación del pedido a "Pago antes de envío" en la \
                    pestaña "Otra información"'
            raise Warning(_(msg))
            return False
        # We compare date between invoices and today, not allow 15 day delay
        domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'open')]
        open_invoices = self.env['account.invoice'].search(domain)
	ahora = datetime.now()	
	date_list = []
	count=0
        for x in open_invoices:		
                date_inv = datetime.strptime(x.date_due, '%Y-%m-%d')
		date_list.append(date_inv)
		
	for i in date_list:
		dif = str((ahora-date_list[count]).days)
		if ahora>date_list[count]:
               		if int(dif) > 15:
                       		msg = 'El Cliente tiene facturas vencidas con mas de 15 días de atrazo!'
                       		raise Warning(_(msg))
                       		return False
		count=count+1

        return True
    _columns = {
        'sale_order_aprobe': fields.boolean(string='Aprobado', help="Aprobación de Gerencia Comercial"),
    }
sale_order()

