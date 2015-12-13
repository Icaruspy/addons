# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp.osv import fields,osv
from openerp.tools.sql import drop_view_if_exists

class bank_statement_report(osv.osv):
    _name = "bank.statement.report"
    _description = "Bank Statement Análisis"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    _columns = {
        'date': fields.date('Fecha Rendición', readonly=True),
        'statement_id': fields.many2one('account.bank.statement', 'Rendición', readonly=True),
        'cliente': fields.char('Cliente', size=128, readonly=True),
        'journal_id': fields.many2one('account.journal', 'Diario', readonly=True),
        'collector': fields.many2one('res.users', 'Cobrador', readonly=True),
        'name': fields.char('Ref.', size=128, readonly=True),
        'voucher_id': fields.many2one('account.voucher', 'Cobro/Pago', readonly=True),
        'number': fields.char('Ref. Cob/Pag', size=128, readonly=True),
        'receipt_id': fields.many2one('account.voucher.receipt', 'Recibo',readonly=True),
        'create_uid': fields.many2one('res.users', 'Contable', readonly=True),
        'nro_chk': fields.integer('Nro. Chk', readonly=True, group_operator='min'),
        'payment_date': fields.date('Fecha Pago', readonly=True),
        'issue_date': fields.date('Fecha Cheque', readonly=True),
        'x_titular': fields.char('Titular', size=128, readonly=True),
        'amount': fields.float('Monto', readonly=True, digits_compute=dp.get_precision('Account')),

    }


    def init(self, cr):
        drop_view_if_exists(cr, 'bank_statement_report')
        cr.execute("""
  CREATE OR REPLACE VIEW bank_statement_report AS 
   SELECT sub.id,
    sub.date,
    sub.statement_id,
    sub.cliente,
    sub.journal_id,
    sub.collector,
    sub.name,
    sub.voucher_id,
    sub.number,
    sub.amount,
    sub.receipt_id,
    sub.create_uid,
    sub.nro_chk,
    sub.payment_date,
    sub.issue_date,
    sub.x_titular
   FROM ( SELECT min(absl.id) AS id,
            absl.date,
            absl.statement_id,
            rs.name AS cliente,
            av.journal_id,
            av.collector,
            absl.name,
            absl.voucher_id,
            av.number,
            av.amount,
            av.receipt_id,
            absl.create_uid,
            ack.number AS nro_chk,
            ack.payment_date,
            ack.issue_date,
            ack.x_titular
           FROM account_bank_statement_line absl
             LEFT JOIN account_voucher av ON absl.voucher_id = av.id
             LEFT JOIN account_check ack ON av.id = ack.voucher_id
             LEFT JOIN res_partner rs ON absl.partner_id = rs.id
          GROUP BY absl.date, absl.statement_id, rs.name, av.journal_id, av.collector, absl.name, absl.voucher_id, av.number, av.amount, av.receipt_id, absl.create_uid, ack.number, ack.payment_date, ack.issue_date, ack.x_titular
          ORDER BY absl.date, av.collector, av.journal_id, rs.name 
          ) sub;
            """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
