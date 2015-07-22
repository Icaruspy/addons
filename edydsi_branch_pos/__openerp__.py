# -*- coding: utf-8 -*-
{
    'name': "edydsi_branch_pos",

    'summary': """
        EDYDSI Branch on POS""",

    'description': """
        Implement the branch concept on POS, according with Paraguay's rules
    """,

    'author': "NUMA Extreme Systems",
    'website': "http://www.numaes.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'edydsi_branches',
                'point_of_sale'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pos_config_view.xml',
        'views/pos_order_view.xml',
        'views/sales_point_view.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'data/demo.xml',
    ],
    'qweb': [
        'static/src/xml/extended_pos.xml',
    ],
    'installable': True,
    'auto_install': True,

}
