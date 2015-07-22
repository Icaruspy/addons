# -*- coding: utf-8 -*-
{
    'name': "invoice_printing",

    'summary': """
        Preprinted Invoice""",

    'description': """
        Implement a preprinted invoice report for invoices
    """,

    'author': "Camilo Ramirez",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'report'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/invoice_printing_view.xml',
        'report_paperformat.xml',
        'report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': True,

}
