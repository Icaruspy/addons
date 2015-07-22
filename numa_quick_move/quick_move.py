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


from openerp.osv.osv import Model, TransientModel, except_osv
from openerp.osv import fields
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2011 NUMA Extreme Systems (<http:www.numaes.com>).
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
from openerp import tools

import logging
_logger = logging.getLogger(__name__)

class quick_move_category(Model):
    _name = "account.quick_move_category"

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'description': fields.text('Description'),
    }

class quick_move(Model):
    '''
    An account quick move is way to assign fixed accounts to repetitive movements, like witholding taxes or retentions on payment
    In a receipt or payment, they could be used to avoid repetive input of account numbers, assigning an amount to be used for credit
    and debit on the credit account and the debit account.
    Use of this quick move implies no change on the balance of the move, since the same amount will be applied as a credit or debit
    '''
    _name = "account.quick_move"

    _columns = {
        'name':fields.char('Name', size=128, help="Operation code", required=True),
        'description':fields.text('Description', required=True),
        'category': fields.many2one('account.quick_move_category', 'Category'),
        'type': fields.selection([
                    ('received_retention', 'Received retention'),
                    ('received_perception', 'Received perception'),
                    ('supplier_retention', 'Suplier retention')],
                    'Type', required=True),
        'property_qm_credit_account': fields.property(
            type='many2one',
            relation='account.account',
            string="Credit Account",
            help="This account will be used for credit amounts."),
        'property_qm_debit_account': fields.property(
            type='many2one',
            relation='account.account',
            string="Debit Account",
            help="This account will be used for debit amounts."),
        'property_qm_analytic_account': fields.property(
            type='many2one',
            relation='account.analytic.account',
            string="Analytic",
            help="This account will be used for analytic movements."),
    }

    _defaults = {
        'type': 'received_retention',
    }

