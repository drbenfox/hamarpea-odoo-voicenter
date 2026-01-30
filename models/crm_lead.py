# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    voicenter_call_count = fields.Integer(
        'Call Count',
        compute='_compute_voicenter_call_count'
    )
    
    voicenter_last_call_date = fields.Datetime(
        'Last Call',
        compute='_compute_voicenter_last_call'
    )

    def _compute_voicenter_call_count(self):
        """Count calls linked to this lead"""
        for lead in self:
            lead.voicenter_call_count = self.env['voicenter.call.log'].search_count([
                ('lead_id', '=', lead.id)
            ])

    def _compute_voicenter_last_call(self):
        """Get last call date"""
        for lead in self:
            last_call = self.env['voicenter.call.log'].search([
                ('lead_id', '=', lead.id)
            ], order='date desc', limit=1)
            lead.voicenter_last_call_date = last_call.date if last_call else False

    def action_view_calls(self):
        """Open call log list view for this lead"""
        self.ensure_one()
        return {
            'name': f'Calls - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'voicenter.call.log',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }
