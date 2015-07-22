# -*- coding: utf-8 -*-

from openerp import models, fields, api

class res_branch(models.Model):
    _name = 'res.branch'
    
    def _get_default_country(self, cr, uid, context=None):
        company_obj = self.pool['res.company']

        default_company_id = company_obj._company_default_get(cr, uid, 
                                                              'res.branch', 
                                                              context=context)
        if default_company_id:
            default_company = company_obj.browse(cr, uid, 
                                                 default_company_id,
                                                 context=context)
            return default_company.country_id and default_company.country_id.id
        else:
            return False                                         

    name = fields.Char('Name')
    street = fields.Char('Street and door')
    city = fields.Char('City')
    zip = fields.Char('Zip')
    fed_state = fields.Many2one('res.country.state', 'Fed.State',
                                domain="[('country_id','=',country)]",
                                context="{'default_country_id': country}")
    country = fields.Many2one('res.country', 'Country')
    
    company = fields.Many2one('res.company', 'Company',
                              ondelete='cascade',
                              required=True)
    phone = fields.Char('Phone')
    legal_id = fields.Char('Legal ID', size=4)

    default_sales_point = fields.Many2one('res.sales_point', 'Default Sales Point',
                                          domain="[('company','=',company),('usage','=','general')]")
    
    _defaults = {
        'company': lambda s, cr, uid, c: s.pool['res.company']._company_default_get(cr, uid, 'res.branch', context=c),
        'country': _get_default_country,
        'legal_id': '0001',
    }

    _sql_constraints = [
        ('branch_legal_id_company_uniq', 'unique (legal_id,company_id)', 'The branch legal ID must be unique per company!'),
        ('branch_name_company_uniq', 'unique (name,company_id)', 'The branch name must be unique per company!'),
    ]
    
    @api.onchange('fed_state')
    def onchange_fed_state(self):
        if self.fed_state.country_id:
            self.country = self.fed_state.country_id

    @api.onchange('country')
    def onchange_country(self):
        if self.fed_state:
            self.fed_state = False

    