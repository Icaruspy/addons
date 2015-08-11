from openerp import fields, models, api

class sale_order(models.Model):
    '''
    extension to existing sale.order model
    '''
    _inherit = 'sale.order'
    
    state = fields.Selection(selection_add=[('quotation_approved', "Quotation Approved")])
    
    @api.one
    def action_quotation_approve(self):
        self.state = 'quotation_approved'
