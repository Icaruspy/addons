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

import time
from openerp.osv import osv
from openerp.report import report_sxw


class report_print_cheque(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_print_cheque, self).__init__(cr, uid, name, context)
        self.number_lines = 0
        self.number_add = 0
        self.localcontext.update({
            'time': time,
            'fill_stars' : self.fill_stars,
        })

    def fill_stars(self, amount):
        if len(amount) < 100:
            stars = 100 - len(amount)
            return ' '.join([amount,'*'*stars])

        else: return amount


class report_check(osv.AbstractModel):
    _name = 'report.numa_cp_test_bank.report_cheque'
    _inherit = 'report.abstract_report'
    _template = 'numa_cp_test_bank.report_cheque'
    _wrapped_report_class = report_print_cheque

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
