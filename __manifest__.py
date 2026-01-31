# -*- coding: utf-8 -*-
{
    'name': 'Hamarpea Voicenter Integration',
    'version': '18.0.1.0.0',
    'category': 'VOIP',
    'summary': 'Integrate Voicenter VOIP call logs with Odoo CRM',
    'description': """
        Voicenter Integration
        =====================
        
        This module integrates Voicenter VOIP system with Odoo:
        
        Features:
        ---------
        * Automatic call log synchronization from Voicenter API
        * Link calls to contacts and leads automatically
        * Smart buttons on contacts to view call history
        * Auto-create leads for unknown callers
        * Configurable sync intervals with smart scheduling
        * Identify unclosed/missed calls for follow-up
        * Call KPI dashboard and reports
        * Track all call details (duration, status, recordings, etc.)
    """,
    'author': 'drbenfox@hamarpea.com',
    'website': 'https://www.hamarpea.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'crm',
        'contacts',
        'mail',
        'web_tree_many2one_clickable',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/voicenter_call_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
