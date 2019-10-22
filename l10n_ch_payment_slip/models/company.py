# Copyright 2012-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields


class ResCompany(models.Model):
    """Add ISR vertical/horizontal print delta and functionalities."""
    _inherit = "res.company"

    isr_delta_horz = fields.Float(
        'ISR Horz. Delta (inch)',
        help='horiz. delta in inch 1.2 will print the ISR 1.2 inch on the '
             'left, negative value is possible'
    )

    isr_delta_vert = fields.Float(
        'ISR Vert. Delta (inch)',
        help='vert. delta in inch 1.2 will print the ISR 1.2 inch lower,'
             ' negative value is possible'
    )

    isr_scan_line_vert = fields.Float(
        'ISR vert. position for scan line (inch)',
        help='Vert. position in inch for scan line'
    )

    isr_scan_line_horz = fields.Float(
        'ISR horiz. position for scan line(inch)',
        help='Horiz. position in inch for scan line'
    )

    isr_add_vert = fields.Float(
        'ISR vert. position for address (inch)',
        help='Vert. position in inch for address'
    )

    isr_add_horz = fields.Float(
        'ISR horiz. position address (inch)',
        help='Horiz. position in inch for address'
    )

    isr_scan_line_font_size = fields.Integer(
        'ISR scan line font size (pt)',
    )

    isr_scan_line_letter_spacing = fields.Float(
        'ISR scan line letter spacing',
    )

    isr_amount_line_horz = fields.Float(
        'ISR horiz. position for amount line (inch)',
        help='Horiz. position in inch for amount line',
        default=0.00
    )

    isr_amount_line_vert = fields.Float(
        'ISR vert. position for amount line (inch)',
        help='Vert. position in inch for amount line',
        default=0.00,
    )

    merge_mode = fields.Selection(
        [('in_memory', 'Merge Slips in Memory, faster but can exhaust memory'),
         ('on_disk', 'Merge Slips on Disk, slower but safer')],
        string="Payment Slips Merge Mode",
        required=True,
        default="in_memory"
    )
    isr_background = fields.Boolean(
        'Insert ISR background ?',
    )

    isr_header_partner_address = fields.Boolean(
        'Header partner address',
        default=False,
        help='Enabling this will print partner address top-right on the '
             'page header',
    )

