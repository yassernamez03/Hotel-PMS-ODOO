# -*- coding: utf-8 -*-
from odoo import models, fields


class HotelRoom(models.Model):
    _name = 'hotel.rooms'
    _description = 'Hotel Room'
    
    name = fields.Char('Name', required=True)
    room_id = fields.Char('Room Id', size=8, required=True)
    room_type = fields.Many2one('hotel.room_type',required=True)
    status = fields.Boolean(string = "Avalibale", required = True, default=True)
    board_meal = fields.Many2one('hotel.room_board',required=False)

