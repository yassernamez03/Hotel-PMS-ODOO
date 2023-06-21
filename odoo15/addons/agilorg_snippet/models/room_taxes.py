# -*- coding: utf-8 -*-
from odoo import models, fields

TAX_RULE = [('pax_night','Per Night and Pax'),
            ('night','Per Night'),
            ('per_pax', 'Per Pax'),
            ('stay', 'Percentage of the stay amount')
            ]

TAX_TYPES = [('amount','Amount'),
             ('percent', 'Percent'),
            ]

class PmsTaxes(models.Model):
    _name = 'hotel.room.taxes'
    _description = 'Room Taxes'
    
    name = fields.Char('Taxe Name')
    code = fields.Char('Taxe Code', required=False)
    tax_rule = fields.Selection(TAX_RULE,
                                string='Tax Rule',
                                default='pax_night',
                                required=True)
    value = fields.Float(string='Amount', digits='Taxe Value')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    type = fields.Selection(TAX_TYPES,
                            string='Type',
                            default='amount',
                            required=True)
    description = fields.Char('Description')

