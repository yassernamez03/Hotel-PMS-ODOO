# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class Main(http.Controller):
    
    @http.route('/rooms', type='http', auth="user", website=True)
    def hotel_rooms(self):
        return request.render(
            'agilorg_snippet.rooms', {
                'rooms': request.env['hotel.room_type'].search([]),
            })
    @http.route('/rooms/<model("hotel.room_type"):room>', type='http', auth="user", website=True)
    def hotel_rooms_detail(self, room):
        return request.render(
            'agilorg_snippet.room_detail', {
                'room': room,
            })
    @http.route('/booking/rooms', type='http', auth="user", website=True)
    def hotel_rooms_avalibility(self):
        return request.render(
            'agilorg_snippet.rooms_avalibility', {
                'rooms': request.env['hotel.room_type'].search([]),
            })