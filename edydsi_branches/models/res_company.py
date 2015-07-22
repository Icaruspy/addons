# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _

class res_company(models.Model):
    _inherit = 'res.company'
    
    branches = fields.One2many('res.branch', 'company', 'Branches')
    sales_points = fields.One2many('res.sales_point', 'company', 'Sales Points')    

    @api.multi
    def action_open_branches(self):
        assert len(self)==1, 'Just one at the time'
        
        company = self

        new_context = self.env.context.copy()
        new_context.update({'default_company': company.id, 
                            'search_default_company': [company.id]})

        return {
            'name':_("Branches for %s") % company.name, 
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'res.branch',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': "[('company', '=', %d)]" % company.id,
            'context': new_context,
        }
        
    @api.multi
    def action_open_sales_points(self):
        assert len(self)==1, 'Just one at the time'
        
        company = self

        new_context = self.env.context.copy()
        new_context.update({'default_company': company.id, 
                            'search_default_company': [company.id]})

        return {
            'name':_("Sales points for %s") % company.name, 
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'res.sales_point',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': "[('company', '=', %d)]" % company.id,
            'context': new_context,
        }
        
        