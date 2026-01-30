# Voicenter Integration for Odoo 18

## Description

This module integrates Voicenter VOIP system with Odoo, providing comprehensive call tracking and CRM integration.

## Features

- **Automatic Call Log Synchronization**: Fetches call logs from Voicenter API automatically
- **Smart Scheduling**: More frequent sync during business hours, less frequent at night
- **Contact Matching**: Automatically links calls to existing contacts and leads
- **Auto Lead Creation**: Creates new leads for unknown incoming callers
- **Smart Buttons**: View call history directly from contact and lead forms
- **Follow-up Tracking**: Identifies "unclosed" call series that need follow-up
- **Activity Creation**: Automatically creates follow-up activities for missed calls
- **Call Analytics**: Pivot tables and graphs for call KPIs
- **Recording Access**: Direct links to call recordings

## Configuration

1. Go to Settings > Voicenter Integration
2. Enter your Voicenter API token
3. Configure sync intervals for peak and off-peak hours
4. Set your business hours
5. Enable/disable auto-lead creation and activity creation
6. Click "Sync Now" to test the connection

## Usage

### Viewing Calls

- **Voicenter > Calls > All Calls**: View all synced call logs
- **Voicenter > Calls > Missed Calls**: View missed calls needing follow-up
- **Contact Form > Phone Calls button**: View all calls for a specific contact
- **Lead Form > Phone Calls button**: View all calls for a specific lead

### Call Analysis

Use the pivot table and graph views to analyze:
- Calls per day/week/month
- Calls per representative
- Average call duration
- Missed call rates

### Follow-up Management

- Missed calls automatically create activities on contacts/leads (if enabled)
- Use the "Needs Follow-up" filter to see calls requiring attention
- Mark follow-ups as done directly from the call form

## Technical Details

### Models

- `voicenter.call.log`: Stores all call detail records (CDR)
- `res.partner`: Extended with call statistics and smart button
- `crm.lead`: Extended with call statistics and smart button
- `res.config.settings`: Voicenter configuration settings

### Scheduled Actions

- **Smart Sync Cron**: Runs every 5 minutes, but only syncs based on configured intervals
  - Peak hours: default 5 minutes
  - Off-peak hours: default 30 minutes

### Security

- Users: Can view call logs
- Sales Users: Can view and edit call logs
- Sales Managers: Full access including create/delete

## Dependencies

- `base`
- `crm`
- `contacts`

## License

LGPL-3

## Author

Your Clinic

## Support

For issues or questions, please contact your system administrator.
