# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    voicenter_api_token = fields.Char(
        string='Voicenter API Token',
        config_parameter='voicenter.api_token',
        help='Your Voicenter API authentication token'
    )
    
    voicenter_sync_interval = fields.Integer(
        string='Sync Interval (minutes)',
        config_parameter='voicenter.sync_interval',
        default=15,
        help='How often to sync call logs from Voicenter (in minutes)'
    )
    
    voicenter_business_hours_start = fields.Integer(
        string='Business Hours Start',
        config_parameter='voicenter.business_hours_start',
        default=8,
        help='Start of business hours (0-23)'
    )
    
    voicenter_business_hours_end = fields.Integer(
        string='Business Hours End',
        config_parameter='voicenter.business_hours_end',
        default=18,
        help='End of business hours (0-23)'
    )
    
    voicenter_peak_sync_interval = fields.Integer(
        string='Peak Hours Sync Interval (minutes)',
        config_parameter='voicenter.peak_sync_interval',
        default=5,
        help='Sync interval during business hours (in minutes)'
    )
    
    voicenter_off_peak_sync_interval = fields.Integer(
        string='Off-Peak Sync Interval (minutes)',
        config_parameter='voicenter.off_peak_sync_interval',
        default=30,
        help='Sync interval outside business hours (in minutes)'
    )
    
    voicenter_auto_create_leads = fields.Boolean(
        string='Auto-Create Leads',
        config_parameter='voicenter.auto_create_leads',
        default=True,
        help='Automatically create leads for unknown incoming callers'
    )
    
    voicenter_create_activities = fields.Boolean(
        string='Create Follow-up Activities',
        config_parameter='voicenter.create_activities',
        default=True,
        help='Automatically create activities for missed calls needing follow-up'
    )

    def action_sync_now(self):
        """Manual sync button"""
        self.env['voicenter.call.log'].sync_from_voicenter(hours_back=24)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Voicenter Sync',
                'message': 'Call logs sync initiated',
                'type': 'success',
                'sticky': False,
            }
        }
