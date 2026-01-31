# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    voicenter_api_token = fields.Char(
        string='Voicenter API Token',
        config_parameter='voicenter.api_token',
        help='Your Voicenter API authentication token'
    )

    voicenter_sync_enabled = fields.Boolean(
        string='Enable Automatic Sync',
        config_parameter='voicenter.sync_enabled',
        default=True,
        help='Enable or disable automatic call log synchronization'
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

    def set_values(self):
        """Override to add validation before saving config parameters"""
        # Validate business hours
        if self.voicenter_business_hours_start < 0 or self.voicenter_business_hours_start > 23:
            raise ValidationError(_('Business hours start must be between 0 and 23'))
        if self.voicenter_business_hours_end < 0 or self.voicenter_business_hours_end > 23:
            raise ValidationError(_('Business hours end must be between 0 and 23'))
        if self.voicenter_business_hours_start >= self.voicenter_business_hours_end:
            raise ValidationError(_('Business hours start must be before end time'))

        # Validate sync intervals
        if self.voicenter_peak_sync_interval < 1 or self.voicenter_peak_sync_interval > 60:
            raise ValidationError(_('Peak sync interval must be between 1 and 60 minutes'))
        if self.voicenter_off_peak_sync_interval < 1 or self.voicenter_off_peak_sync_interval > 60:
            raise ValidationError(_('Off-peak sync interval must be between 1 and 60 minutes'))

        super(ResConfigSettings, self).set_values()

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
