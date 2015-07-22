# -*- coding: utf-8 -*-
from openerp import http

# class EdydsiBranches(http.Controller):
#     @http.route('/edydsi_branches/edydsi_branches/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/edydsi_branches/edydsi_branches/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('edydsi_branches.listing', {
#             'root': '/edydsi_branches/edydsi_branches',
#             'objects': http.request.env['edydsi_branches.edydsi_branches'].search([]),
#         })

#     @http.route('/edydsi_branches/edydsi_branches/objects/<model("edydsi_branches.edydsi_branches"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('edydsi_branches.object', {
#             'object': obj
#         })