# -*- coding: utf-8 -*-
############################################################################
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
from openerp.osv import osv


class product_product(osv.Model):
    _inherit = "product.product"

    def copy(self, cr, uid,
             id, default=None, context=None):  # pylint: disable=W0622

        if not default:
            default = {}

        product_default_code = self.browse(cr, uid, id, context=context)

        default[
            'ean13'] = product_ean13.ean13 and\
            product_ean13.ean13 + ' (copy)' or False

        return super(product_product, self).copy(cr, uid, id, default=default,
                                                 context=context)

    _sql_constraints = [
        ('ean13_unique', 'unique (ean13)',
         'The code of Product must be unique !'),
    ]
