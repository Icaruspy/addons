# -*- coding: utf-8 -*-

from openerp import models, fields, api

class res_sales_point(models.Model):
    _name = 'res.sales_point'
    
    @api.depends('timbrado','timbrado_due_date')
    def _is_valid(self):
        for sp in self:
            if sp.timbrado and \
               sp.timbrado_due_date and \
               sp.timbrado_due_date >= fields.Date.context_today(self):
                sp.is_valid = True
            else:
                sp.is_valid = False

    name = fields.Char('Name')
    company = fields.Many2one('res.company', 'Company',
                              ondelete='cascade',
                              required=True)

    legal_id = fields.Char('Legal ID', size=3)
    timbrado = fields.Char('Timbrado')
    timbrado_due_date = fields.Date('Vencimiento')
    is_valid = fields.Boolean('Is valid?',
                              compute=_is_valid)

    sequence = fields.Many2one('ir.sequence', 'Order IDs Sequence', 
                               copy=False, 
            help="This sequence is automatically created by Odoo but you can change it "\
                "to customize the reference numbers of your orders.")
    sequence_next = fields.Integer('Next value',
                                   related='sequence.number_next',
                                   readonly=True)
                
    usage = fields.Selection([
                    ('general', 'General'),
                    ('pos', 'Point of Sales')], 'Usage', required=True)
    
    _defaults = {
        'usage': 'general',
        'company': lambda s, cr, uid, c: 
                        s.pool['res.company']._company_default_get(cr, uid, 
                                                                   'res.branch', 
                                                                   context=c),
        'legal_id': '001',
    }

    _sql_constraints = [
        ('sales_point_legal_id_company_uniq', 'unique (legal_id,company_id)', 'The sales point legal ID must be unique per company!'),
        ('sales_point_name_company_uniq', 'unique (name,company_id)', 'The sales point name must be unique per company!'),
    ]
    
    def create(self, cr, uid, vals, context=None):
        vals = vals or {}
        sequence_obj = self.pool['ir.sequence']
        if 'sequence' not in vals:
            vals['sequence'] = sequence_obj.create(cr, uid, {
                'name': 'Sales Point Tickets %s' % vals.get['name'],
                'padding': 8,
                'prefix': "",
                'code': "res.sales_point",
                'company_id': vals.get('company', False),
            }, context=context)
        return super(res_sales_point, self).create(cr, uid, vals, context=context)

