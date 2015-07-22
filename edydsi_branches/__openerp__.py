# -*- coding: utf-8 -*-
{
    'name': "edydsi_branches",

    'summary': """
        EDYDSI Branches""",

    'description': """
        Creates the concept of branches, as an extended sales shop (as it was till v8)
    """,

    'author': "NUMA Extreme Systems",
    'website': "http://www.numaes.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/branch_view.xml',
        'views/sales_point_view.xml',
        'views/res_company_view.xml',
        'views/account_invoice_view.xml',
        'static/src/xml/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'auto_install': False,

}
