# -*- coding: utf-8 -*-
from odoo import models, fields


class RoomFeatures(models.Model):
    _name = 'hotel.room.feature'
    _description = 'Room feature'
    
    name = fields.Char('Name', required=True)
    image = fields.Binary(attachment=True)
    description = fields.Char('Description')

