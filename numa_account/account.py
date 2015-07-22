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
from openerp import tools
from datetime import datetime, timedelta, date

import logging
_logger = logging.getLogger(__name__)

class account_move(Model):
    _inherit = 'account.move'

    def revert (self, cr, uid, ids, vals, context=None):
        # Generate a counter movement
        # It returns a dictionary, keyed by id, with the new moves
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_line_obj = self.pool.get('account.move.line')

        res = {}        
        for move in self.browse (cr, uid, ids, context=context):
            # Generate the new movement and reconcile with previous one
            # in order to properly adjust debt
            
            if move.state != 'posted':
                raise except_osv(_('Error !'), _('You can not revert a move [%(name)%s] in this state [%(state)s]!') % {
                                                                'name': move.name,
                                                                'state': move.state})

            # Generate new move, recording new move_lines and its relation
            vals = {
                'line_id': [], 
                'date': fields.date.context_today(self, cr, uid, context=context)
            }
            new_move_id = self.copy (cr, uid, move.id, vals, context=context)
            ml_ids = []
            for ml in move.line_id:
                vals = {
                    'move_id': new_move_id,
                    'credit': ml.debit,
                    'debit': ml.credit,
                }
                ml_ids.append((ml.id, move_line_obj.copy(cr, uid, ml.id, vals, context=context)))
            self.post (cr, uid, [new_move_id], context=context)

            for original_id, new_id in ml_ids:
                ml = move_line_obj.browse(cr, uid, original_id, context=context)
                if ml.reconcile_id:
                    for ml1 in ml.reconcile_id.line_id:
                        ml1.write({'reconcile_partial_id': ml.reconcile_id.id, 'reconcile_id': False})
                    ml.refresh()
                move_line_obj.reconcile_partial(cr, uid, [ml.id, new_id])

            res[move.id] = new_move_id
    
        return res

