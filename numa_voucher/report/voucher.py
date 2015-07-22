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

import time
from openerp.report import report_sxw

to_29 = ( 'cero',  'un',   'dos',  'tres', 'cuatro',   'cinco',   'seis',
          'siete', 'ocho', 'nueve', 'diez',   'once', 'doce', 'trece',
          'catorce', 'quince', 'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve',
          'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
          'veintiseis', 'veintisiete', 'veintiocho', 'veintinueve' )

tens  = ( 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa')
hundreds = ( 'cien', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos')
denom = ( '', 'mil', 'millón', 'mil millones', 'billón', 'mil de billones',)
denom2 = ( '', 'miles','millones', 'miles de millones', 'billones', 'miles de billones',)
# convert a value < 100 to Spanish.
def _convert_nn(val):
    if val == 20:
        return tens[0]
    if val < 20:
        return to_29[val]

    if val % 10 == 0:
        return tens[(val//10)-2]

    return tens[(val // 10)-2] + ' y ' + to_29[val % 10]

# convert a value < 1000 to spanish, special cased because it is the level that kicks 
# off the < 100 special case.  The rest are more general.  This also allows you to
# get strings in the form of 'forty-five hundred' if called directly.
def _convert_nnn(val):
    if val < 100:
        return _convert_nn(val)
    if val < 200:
        return 'ciento '+_convert_nn(val-100)
    if val % 100 == 0:
        return hundreds[val // 100 - 1]

    return hundreds[val // 100 - 1]+' '+_convert_nn(val % 100)

def spanish_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
         return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            if l < 200:
                ret = _convert_nnn(l) + ' ' + denom[didx]
            else:
                ret = _convert_nnn(l) + ' ' + denom2[didx]
            if r > 0:
                ret = ret + ' ' + spanish_number(r)
            return ret

def amount_to_text(number, currency):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = spanish_number(int(list[0]))
    end_word = spanish_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and 'centavos' or 'centavo'
    final_result = start_word +' '+units_name+' con ' + end_word +' '+cents_name
    return final_result

class report_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_voucher, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert':self.convert,
            'suma': self.suma,
            'get_doc_desc': self.get_doc_desc,
        })

    def convert(self, amount, cur):
        amt_words = amount_to_text(amount, cur or '')
        return amt_words.capitalize()

    def suma (self, array):
        if not array:
            return 0.0

        s = 0.0
        for x in array:
            s += x.amount or 0.0
        return s

    def get_doc_desc(self, doc):
        if doc.type == 'cheque':
            s = u"Banco: %s, Cheque Nro: %s, Titular: %s, CUIT: %s, Venc: %s" % (doc.issuer.bank.name, doc.name, doc.issuer.owner_name, doc.issuer.cuit, doc.maturity_date)
        elif doc.type == 'pagare':
            s = u"Pagaré Titular: %s, Nro: %s, CUIT: %s, Venc: %s" % (doc.issuer.owner_name, doc.name, doc.issuer.cuit, doc.maturity_date)
        else:
            s = u"Doc.a Pagar Titular: %s, Nro: %s, CUIT: %s, Venc: %s" % (doc.issuer.owner_name, doc.name, doc.issuer.cuit, doc.maturity_date)

        return s


report_sxw.report_sxw(
    'report.customer_voucher_print',
    'account.customer_voucher',
    'addons/numa_voucher/report/customer_voucher.rml',
    parser=report_voucher,header="external"
)

report_sxw.report_sxw(
    'report.payment_order_print',
    'account.supplier_voucher',
    'addons/numa_voucher/report/supplier_voucher.rml',
    parser=report_voucher,header="external"
)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
