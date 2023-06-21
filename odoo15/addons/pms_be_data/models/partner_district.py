# -*- coding: utf-8 -*-
from odoo import models, fields, api


class City(models.Model):
    _inherit = 'res.city'

    code = fields.Char("Code")
    district_ids = fields.One2many('res.city.district','city_id',string='Districts')


class PartnerDistrict(models.Model):
    _name = "res.city.district"
    _description = "City District"

    name = fields.Char(string="District name")
    code = fields.Char("Code")
    country_id = fields.Many2one('res.country', string="Country", required=1)
    city_id = fields.Many2one('res.city', string="City", required=1)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            city_ids = self.env['res.city'].search([('country_id', '=', self.country_id.id)])
            return {
                'domain': {'city_id': [('id', 'in', city_ids.ids)], }
            }
