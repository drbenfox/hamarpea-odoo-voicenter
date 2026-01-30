# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
from datetime import datetime, timedelta
import json

_logger = logging.getLogger(__name__)


class VoicenterCallLog(models.Model):
    _name = 'voicenter.call.log'
    _description = 'Voicenter Call Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'call_id'

    # Core identification fields
    call_id = fields.Char('Call ID', required=True, index=True, copy=False)
    date = fields.Datetime('Call Date', required=True, index=True)

    # Call participants
    caller_number = fields.Char('Caller Number', index=True)
    target_number = fields.Char('Target Number', index=True)
    caller_extension = fields.Char('Caller Extension')
    target_extension = fields.Char('Target Extension')
    did = fields.Char('DID Number')

    # Call details
    duration = fields.Integer('Duration (seconds)',
                              help='Actual conversation duration')
    ring_time = fields.Integer(
        'Ring Time (seconds)', help='Ringing duration before answer')
    call_type = fields.Char('Call Type')
    cdr_type = fields.Integer('CDR Type ID')
    dial_status = fields.Char('Dial Status')

    # Recording
    record_url = fields.Char('Recording URL')
    record_expect = fields.Boolean('Recording Expected')

    # Representative/User info
    representative_name = fields.Char('Representative Name')
    representative_code = fields.Char('Representative Code')
    user_name = fields.Char('User Name')

    # Department/Account
    department_name = fields.Char('Department Name')
    department_id_ext = fields.Integer('Department ID (External)')

    # Queue info
    queue_name = fields.Char('Queue Name')

    # Cost
    price = fields.Float('Price (Agorot)', digits=(16, 2),
                         help='Price in Israeli Agorot')

    # Destination
    target_prefix_name = fields.Char('Destination Country')

    # IVR and Custom Data
    dtmf_data = fields.Text('DTMF Data (JSON)')
    custom_data = fields.Text('Custom Data (JSON)')

    # Odoo Relations
    partner_id = fields.Many2one('res.partner', string='Contact', index=True,
                                 ondelete='set null')
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity', index=True,
                              ondelete='set null')

    # Computed/helper fields
    partner_name = fields.Char(
        related='partner_id.name', string='Contact Name', store=True)
    lead_name = fields.Char(related='lead_id.name',
                            string='Lead Name', store=True)

    # Call classification
    is_incoming = fields.Boolean(
        'Incoming Call', compute='_compute_call_direction', store=True)
    is_outgoing = fields.Boolean(
        'Outgoing Call', compute='_compute_call_direction', store=True)
    is_answered = fields.Boolean(
        'Answered', compute='_compute_call_status', store=True)
    is_missed = fields.Boolean(
        'Missed/Unanswered', compute='_compute_call_status', store=True)

    # Follow-up tracking
    needs_followup = fields.Boolean('Needs Follow-up', default=False,
                                    help='Set automatically for unclosed call series')
    followup_done = fields.Boolean('Follow-up Completed', default=False)

    # Sync tracking
    synced_at = fields.Datetime('Synced At', default=fields.Datetime.now)

    _sql_constraints = [
        ('call_id_unique', 'UNIQUE(call_id)', 'Call ID must be unique!')
    ]

    @api.depends('cdr_type', 'call_type')
    def _compute_call_direction(self):
        """Determine if call is incoming or outgoing based on CDR type"""
        incoming_types = [
            1, 8, 11, 18, 19]  # Incoming, Queue, VoiceMail, Click2IVR Incoming, Click2Queue
        # Extension Outgoing, Click2Call legs, ProductiveCall legs
        outgoing_types = [4, 9, 10, 14, 15]

        for record in self:
            record.is_incoming = record.cdr_type in incoming_types
            record.is_outgoing = record.cdr_type in outgoing_types

    @api.depends('dial_status')
    def _compute_call_status(self):
        """Determine if call was answered or missed"""
        answered_statuses = ['ANSWER', 'VOICEMAIL']
        missed_statuses = ['NOANSWER', 'CANCEL', 'ABANDONE', 'TIMEOUT', 'BUSY', 'FULL', 'EXIT',
                           'VOEND', 'NOTDIALED', 'NOTCALLED', 'CONGESTION', 'CHANUNAVAIL']

        for record in self:
            record.is_answered = record.dial_status in answered_statuses
            record.is_missed = record.dial_status in missed_statuses

    def _get_phone_numbers_from_call(self):
        """Extract all possible phone numbers from a call record"""
        self.ensure_one()
        phone_numbers = []

        # Add caller number
        if self.caller_number:
            phone_numbers.append(self.caller_number)
            # Also try without country code for Israeli numbers
            if self.caller_number.startswith('972'):
                phone_numbers.append('0' + self.caller_number[3:])

        # Add target number if it's a phone number (not extension)
        if self.target_number and self.target_number.isdigit():
            phone_numbers.append(self.target_number)
            if self.target_number.startswith('972'):
                phone_numbers.append('0' + self.target_number[3:])

        # Add DID
        if self.did:
            phone_numbers.append(self.did)

        return list(set(phone_numbers))  # Remove duplicates

    @api.model
    def _match_partner(self, phone_numbers):
        """Find partner matching any of the phone numbers"""
        if not phone_numbers:
            return False

        Partner = self.env['res.partner']

        # Search in phone, mobile, and sanitized versions
        for phone in phone_numbers:
            # Try exact match first
            partner = Partner.search([
                '|', '|',
                ('phone', '=', phone),
                ('mobile', '=', phone),
                ('phone', 'ilike', phone.replace(' ', '').replace('-', ''))
            ], limit=1)

            if partner:
                return partner

        return False

    @api.model
    def _match_lead(self, phone_numbers):
        """Find lead matching any of the phone numbers"""
        if not phone_numbers:
            return False

        Lead = self.env['crm.lead']

        for phone in phone_numbers:
            lead = Lead.search([
                '|',
                ('phone', '=', phone),
                ('mobile', '=', phone)
            ], limit=1)

            if lead:
                return lead

        return False

    def _link_to_contact_or_lead(self):
        """Link call to existing contact or lead, or create new lead if unknown"""
        self.ensure_one()

        phone_numbers = self._get_phone_numbers_from_call()

        if not phone_numbers:
            _logger.warning(f"No phone numbers found in call {self.call_id}")
            return

        # Try to match existing partner
        partner = self._match_partner(phone_numbers)
        if partner:
            self.partner_id = partner
            _logger.info(
                f"Call {self.call_id} linked to partner {partner.name}")
            return

        # Try to match existing lead
        lead = self._match_lead(phone_numbers)
        if lead:
            self.lead_id = lead
            _logger.info(f"Call {self.call_id} linked to lead {lead.name}")
            return

        # Create new lead for unknown number if it's an incoming call
        if self.is_incoming:
            lead_name = f"Missed Call - {self.caller_number or 'Unknown'}"

            new_lead = self.env['crm.lead'].create({
                'name': lead_name,
                'phone': self.caller_number,
                'type': 'lead',
                'description': f"Missed phone call on {self.date.strftime('%Y-%m-%d %H:%M')}",
            })

            self.lead_id = new_lead
            _logger.info(
                f"Created new lead {new_lead.id} for call {self.call_id}")

    @api.model
    def sync_from_voicenter(self, hours_back=24):
        """
        Sync call logs from Voicenter API

        Args:
            hours_back: Number of hours to look back (default 24)
        """
        ICPSudo = self.env['ir.config_parameter'].sudo()
        api_token = ICPSudo.get_param('voicenter.api_token')

        if not api_token:
            _logger.warning("Voicenter API token not configured")
            return

        # Determine date range
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=hours_back)

        # Check last sync to avoid duplicates
        last_call = self.search([], order='date desc', limit=1)
        if last_call and last_call.date:
            # Add 1 minute to last call date to avoid duplicates
            from_date = max(from_date, last_call.date + timedelta(minutes=1))

        # Format dates for API (ISO 8601, GMT 0)
        from_date_str = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        to_date_str = to_date.strftime("%Y-%m-%dT%H:%M:%S")

        _logger.info(
            f"Syncing Voicenter calls from {from_date_str} to {to_date_str}")

        # Prepare API request
        url = "https://api.voicenter.com/hub/cdr/"

        # All available fields from API
        fields_list = [
            "CallerNumber", "TargetNumber", "Date", "Duration",
            "CallID", "Type", "CdrType", "DialStatus", "TargetExtension",
            "CallerExtension", "DID", "QueueName", "RecordURL", "RecordExpect",
            "Price", "RingTime", "RepresentativeName", "RepresentativeCode",
            "UserName", "DTMFData", "CustomData", "DepartmentName",
            "DepartmentId", "TargetPrefixName"
        ]

        payload = {
            "code": api_token,
            "fields": fields_list,
            "search": {
                "fromdate": from_date_str,
                "todate": to_date_str
            },
            "sort": [{
                "field": "date",
                "order": "desc"
            }]
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('ERROR_NUMBER', 0) != 0:
                _logger.error(
                    f"Voicenter API error: {data.get('ERROR_DESCRIPTION')}")
                return

            cdr_list = data.get('CDR_LIST', [])
            _logger.info(f"Retrieved {len(cdr_list)} calls from Voicenter")

            created_count = 0
            updated_count = 0

            for cdr in cdr_list:
                call_vals = self._prepare_call_values(cdr)

                # Check if call already exists
                existing_call = self.search(
                    [('call_id', '=', call_vals['call_id'])], limit=1)

                if existing_call:
                    existing_call.write(call_vals)
                    updated_count += 1
                else:
                    new_call = self.create(call_vals)
                    new_call._link_to_contact_or_lead()
                    created_count += 1

            _logger.info(
                f"Voicenter sync completed: {created_count} created, {updated_count} updated")

            # After sync, identify unclosed calls
            self._identify_unclosed_calls()

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error syncing from Voicenter: {str(e)}")
            raise UserError(_("Failed to sync from Voicenter: %s") % str(e))

    @api.model
    def _prepare_call_values(self, cdr):
        """Convert API CDR data to Odoo field values"""
        # Parse date
        date_str = cdr.get('Date')
        call_date = False
        if date_str:
            try:
                call_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            except:
                try:
                    call_date = datetime.strptime(
                        date_str, "%Y-%m-%d %H:%M:%S")
                except:
                    _logger.warning(f"Could not parse date: {date_str}")

        return {
            'call_id': cdr.get('CallID'),
            'date': call_date,
            'caller_number': cdr.get('CallerNumber'),
            'target_number': cdr.get('TargetNumber'),
            'caller_extension': cdr.get('CallerExtension'),
            'target_extension': cdr.get('TargetExtension'),
            'did': cdr.get('DID'),
            'duration': cdr.get('Duration', 0),
            'ring_time': cdr.get('RingTime', 0),
            'call_type': cdr.get('Type'),
            'cdr_type': cdr.get('CdrType'),
            'dial_status': cdr.get('DialStatus'),
            'record_url': cdr.get('RecordURL'),
            'record_expect': cdr.get('RecordExpect', False),
            'representative_name': cdr.get('RepresentativeName'),
            'representative_code': cdr.get('RepresentativeCode'),
            'user_name': cdr.get('UserName'),
            'department_name': cdr.get('DepartmentName'),
            'department_id_ext': cdr.get('DepartmentId'),
            'queue_name': cdr.get('QueueName'),
            'price': cdr.get('Price', 0.0),
            'target_prefix_name': cdr.get('TargetPrefixName'),
            'dtmf_data': json.dumps(cdr.get('DTMFData', [])) if cdr.get('DTMFData') else False,
            'custom_data': json.dumps(cdr.get('CustomData', {})) if cdr.get('CustomData') else False,
            'synced_at': fields.Datetime.now(),
        }

    @api.model
    def _identify_unclosed_calls(self):
        """
        Identify call series that are "unclosed" (last call was unanswered)
        This marks calls that need follow-up
        """
        # Get all partners and leads with calls in the last 7 days
        week_ago = datetime.now() - timedelta(days=7)

        recent_calls = self.search([
            ('date', '>=', week_ago),
            '|',
            ('partner_id', '!=', False),
            ('lead_id', '!=', False)
        ])

        # Group by partner/lead
        entities = {}
        for call in recent_calls:
            key = ('partner', call.partner_id.id) if call.partner_id else (
                'lead', call.lead_id.id)
            if key not in entities:
                entities[key] = []
            entities[key].append(call)

        # Check each entity's call series
        for entity_key, calls in entities.items():
            # Sort by date descending
            sorted_calls = sorted(calls, key=lambda c: c.date, reverse=True)

            # Check if most recent call was unanswered
            most_recent = sorted_calls[0]

            if most_recent.is_missed and not most_recent.followup_done:
                most_recent.needs_followup = True
                _logger.info(
                    f"Marked call {most_recent.call_id} as needing follow-up")

                # Optionally create activity for follow-up
                if most_recent.partner_id:
                    self._create_followup_activity(
                        most_recent, most_recent.partner_id)
                elif most_recent.lead_id:
                    self._create_followup_activity(
                        most_recent, most_recent.lead_id)

    def _create_followup_activity(self, call, record):
        """Create a follow-up activity for a missed call, assigned to most recent user who spoke with them"""
        Activity = self.env['mail.activity']

        # Check if activity already exists
        existing = Activity.search([
            ('res_model', '=', record._name),
            ('res_id', '=', record.id),
            ('summary', '=', 'Missed Phone Call')
        ], limit=1)

        if existing:
            return

        activity_type = self.env.ref(
            'mail.mail_activity_data_call', raise_if_not_found=False)
        if not activity_type:
            activity_type = self.env['mail.activity.type'].search(
                [('name', '=', 'Call')], limit=1)

        # SMART ASSIGNMENT: Find most recent user who successfully spoke with this contact
        assigned_user = self._find_most_recent_user_for_contact(record)

        if activity_type:
            # Format phone number as clickable
            phone_html = f'<a href="tel:{call.caller_number}">{call.caller_number}</a>'

            activity_vals = {
                'res_model_id': self.env['ir.model']._get(record._name).id,
                'res_id': record.id,
                'activity_type_id': activity_type.id,
                'summary': 'Missed Phone Call',
                'note': f'From: {phone_html}',
                'date_deadline': fields.Date.today(),
            }

            # Assign to the user if found
            if assigned_user:
                activity_vals['user_id'] = assigned_user.id

            Activity.create(activity_vals)

    def _find_most_recent_user_for_contact(self, record):
        """
        Find the user who most recently had a successful call with this contact/lead

        Args:
            record: res.partner or crm.lead record

        Returns:
            res.users record or False
        """
        # Build domain based on record type
        if record._name == 'res.partner':
            domain = [('partner_id', '=', record.id)]
        elif record._name == 'crm.lead':
            domain = [('lead_id', '=', record.id)]
        else:
            return False

        # Find most recent ANSWERED call
        recent_answered_call = self.search(
            domain + [('is_answered', '=', True)],
            order='date desc',
            limit=1
        )

        if not recent_answered_call:
            return False

        # Get the representative/user from that call
        if recent_answered_call.representative_code:
            # Try to match representative to Odoo user
            # You might need to adjust this based on how your users are set up
            user = self.env['res.users'].search([
                ('name', '=', recent_answered_call.representative_name)
            ], limit=1)

            if user:
                return user

        # Fallback: try to get user from contact/lead
        if hasattr(record, 'user_id') and record.user_id:
            return record.user_id

        return False

    def action_mark_followup_done(self):
        """Mark follow-up as completed"""
        self.write({'followup_done': True, 'needs_followup': False})

    def action_open_recording(self):
        """Open call recording URL"""
        self.ensure_one()
        if not self.record_url:
            raise UserError(_("No recording URL available for this call"))

        return {
            'type': 'ir.actions.act_url',
            'url': self.record_url,
            'target': 'new',
        }

    def action_open_partner(self):
        """Open related partner"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("No contact linked to this call"))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_lead(self):
        """Open related lead"""
        self.ensure_one()
        if not self.lead_id:
            raise UserError(_("No lead linked to this call"))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _cron_smart_sync(self):
        """
        Smart scheduled sync that adjusts frequency based on time of day
        Runs more frequently during business hours, less frequently at night
        """
        ICPSudo = self.env['ir.config_parameter'].sudo()

        # Get configuration
        business_start = int(ICPSudo.get_param(
            'voicenter.business_hours_start', 8))
        business_end = int(ICPSudo.get_param(
            'voicenter.business_hours_end', 18))
        peak_interval = int(ICPSudo.get_param(
            'voicenter.peak_sync_interval', 5))
        off_peak_interval = int(ICPSudo.get_param(
            'voicenter.off_peak_sync_interval', 30))

        # Determine current hour
        current_hour = datetime.now().hour

        # Check if we're in business hours
        is_business_hours = business_start <= current_hour < business_end

        # Get last sync time
        last_call = self.search([], order='synced_at desc', limit=1)
        last_sync = last_call.synced_at if last_call else datetime.now() - \
            timedelta(hours=24)

        minutes_since_sync = (datetime.now() - last_sync).total_seconds() / 60

        # Determine if we should sync
        should_sync = False
        if is_business_hours:
            if minutes_since_sync >= peak_interval:
                should_sync = True
                hours_back = (peak_interval / 60) + 0.5  # Add buffer
        else:
            if minutes_since_sync >= off_peak_interval:
                should_sync = True
                hours_back = (off_peak_interval / 60) + 0.5  # Add buffer

        if should_sync:
            _logger.info(
                f"Running {'business hours' if is_business_hours else 'off-peak'} sync")
            self.sync_from_voicenter(hours_back=hours_back)
        else:
            _logger.debug(
                f"Skipping sync - only {minutes_since_sync:.1f} minutes since last sync")
