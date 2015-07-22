# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA Extreme Systems (www.numaes.com)
#    Copyright (C) 2014
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


{
    'name': 'NUMA Voucher',
    'version': '1.0',
    'category': 'Payment',
    'description': """
NUMA Voucher
============

This module adds the posibility to accept and generate payments
from customers and to suppliers

It expands standard payment managent allowing consolidation of
payments using several types of payments mediums (cash, cheques,
credit cards, etc) into one document, with the posibility to
to consider witholding taxes, retentions and special taxes on
the payment operation (both from customers or to suppliers)

Additionally, it can conciliate customers and suppliers's debts
to payments, and thus simplifiying the conciliation process

Concilation can be managed on generation of the receipt or
payment order, or it can be processed later using specialized
documents.



""",
    'author': 'NUMA Extreme Systems',
    'website': 'http://www.numaes.com',
    'depends': [
        'base',
        'account',
        'numa_quick_move',
        'numa_cheque',
        'numa_credit_card',
        'numa_shared_taxes',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/customer_voucher_view.xml',
        'views/customer_reconcile_view.xml',
        'views/supplier_voucher_view.xml',
        'views/supplier_reconcile_view.xml',
        'report/report_data.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
