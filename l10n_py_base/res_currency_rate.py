# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
# Copyright (C) 2009  Renato Lima - Akretion, Gabriel C. Stabel                 #
#                                                                               #
#This program is free software: you can redistribute it and/or modify           #
#it under the terms of the GNU General Public License as published by           #
#the Free Software Foundation, either version 3 of the License, or              #
#(at your option) any later version.                                            #
#                                                                               #
#This program is distributed in the hope that it will be useful,                #
#but WITHOUT ANY WARRANTY; without even the implied warranty of                 #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                  #
#GNU General Public License for more details.                                   #
#                                                                               #
#You should have received a copy of the GNU General Public License              #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.          #
#################################################################################
 
from openerp.osv import osv, fields

##############################################################################
# Parceiro Personalizado
##############################################################################
class res_currency_rate(osv.osv):

    _inherit = 'res.currency.rate'
    _columns =  {
                     'tasa': fields.integer('Tasa Gs', digits=(16,2), required=True ),
                }
    # funcion para calcular el ratio estandart de trabajo de openerp
    # en paraguay se usa el valor de tasa en guaranies
    def on_change_tasa(self, cr, uid, ids, tasa , rate ):
            rate3 = rate
            rate3 = 1.000000000 / tasa
            return {'value': { 'rate': rate3 } }

res_currency_rate()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
