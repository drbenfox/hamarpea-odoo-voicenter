# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    voicenter_call_count = fields.Integer(
        'Call Count',
        compute='_compute_voicenter_call_count'
    )
    
    voicenter_last_call_date = fields.Datetime(
        'Last Call',
        compute='_compute_voicenter_last_call'
    )
    
    voicenter_total_call_duration = fields.Integer(
        'Total Call Duration (min)',
        compute='_compute_voicenter_call_stats'
    )
    
    voicenter_missed_call_count = fields.Integer(
        'Missed Calls',
        compute='_compute_voicenter_call_stats'
    )

    def _compute_voicenter_call_count(self):
        """Count calls linked to this partner"""
        for partner in self:
            partner.voicenter_call_count = self.env['voicenter.call.log'].search_count([
                ('partner_id', '=', partner.id)
            ])

    def _compute_voicenter_last_call(self):
        """Get last call date"""
        for partner in self:
            last_call = self.env['voicenter.call.log'].search([
                ('partner_id', '=', partner.id)
            ], order='date desc', limit=1)
            partner.voicenter_last_call_date = last_call.date if last_call else False

    def _compute_voicenter_call_stats(self):
        """Compute call statistics"""
        for partner in self:
            calls = self.env['voicenter.call.log'].search([
                ('partner_id', '=', partner.id)
            ])
            
            total_duration = sum(calls.mapped('duration'))
            partner.voicenter_total_call_duration = total_duration // 60  # Convert to minutes
            partner.voicenter_missed_call_count = len(calls.filtered('is_missed'))

    def action_view_calls(self):
        """Open call log list view for this partner"""
        self.ensure_one()
        return {
            'name': f'Calls - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'voicenter.call.log',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
