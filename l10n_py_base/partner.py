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
class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'ruc': fields.char('R.U.C.', size=18 ),
        'documento': fields.char('Numero Documento', size=20 ),
        'nombre_fantasia': fields.char('Nombre Fantasia',size=64),
	'contacto': fields.char('Contacto',size=64),
    }

    _defaults = {
    }

    def ruc_py(self, numero ):
        numero_al=''
        for i in range( len ( numero )):
            c=numero[i]
            codigo=ord( str( c ).upper( ) )
            if not ( codigo >= 48 and codigo <= 57 ):
                numero_al += str( codigo ) 
            else:
                numero_al += numero_al.join( str( c ) )
        k=2
        total=0
        for a in str(numero_al[::-1]):
            if (k>11): k = 2
            total += ( int( a ) * k )
            k = k + 1
        resto = total % 11
        if ( resto > 1 ):
            digito = 11 - resto
        else:
            digito = 0
        return digito


    def _check_ruc(self, cr, uid, ids):
        
        for partner in self.browse(cr, uid, ids):
            if not partner.ruc:
                return True
    
        return self.validate_ruc(partner.ruc)

#        return False

    def validate_ruc(self, ruc):
        # Limpando o Ruc
        if not ruc.isdigit():
            import re
            ruc = re.sub('[^0-9]', '', ruc)
           
        c=str(ruc)[-1]
        retorno=self.ruc_py( str(ruc)[:-1] )
        if ( str(retorno)==str(c) ):
            return True
        else:
            return False            
    

    _constraints = [
                    (_check_ruc, 'RUC invalido!', ['ruc'])
    ]
    
    _sql_constraints = [
                   ('res_partner_ruc_uniq', 'unique (ruc)', 'Ya existe un Socio con este RUC !')
    ]

    def on_change_mask_ruc(self, cr, uid, ids, ruc):

        if  (not ruc):
            return{'value':{}}
        import re
        val = re.sub('[^0-9]', '', ruc)
        if len(val)>0:
            dig=val[-1]
            restante=val[:-1]
            ruc = "%s-%s" % (restante,dig)
            return {'value': {'ruc':ruc}}
        else:
            return {'value': {}}
    
    
res_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
