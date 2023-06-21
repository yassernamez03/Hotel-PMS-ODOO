# -*- coding: utf-8 -*-
from odoo import models, fields


class HotelRoomType(models.Model):
    _name = 'hotel.room_type'
    _description = 'Hotel Room Type'

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id
    
    name = fields.Char('Name', required=True)
    price = fields.Integer('Price', default=0)
    description = fields.Char('Description')
    max_guests = fields.Integer('Max guests',size=1 ,default=1)
    beds = fields.Integer('Beds',size=1, default=1)
    currency_id = fields.Many2one('res.currency', 'Currency', default=_get_default_currency_id, required=True)
    room_feature = fields.Many2many('hotel.room.feature',required=True)
    publish = fields.Boolean(string = "Publish", required = True, default=True)
    room_taxes = fields.Many2many('hotel.room.taxes',required=True)
    image = fields.Binary(attachment=True)
    image1 = fields.Binary(attachment=True)
    image2 = fields.Binary(attachment=True)
    
    description = fields.Char('Description')


