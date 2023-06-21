from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

BE_MOD_ACCOMODATION = 'be.hotels'
BE_MOD_AVAILABILITY = 'be.room.type.availability'
BE_MOD_ROOM_TYPES = 'be.room.type'
BE_MOD_MEAL_BORD = 'be.board'
BE_MOD_RATE_PLAN = 'be.rate.plan'
BE_MOD_ROOM_OCCUPANCY = 'be.room.occupancy'


def daterange(start_date, end_date):
    if end_date >= start_date:
        dif_date = (end_date - start_date).days
        for n in range(int(dif_date) + 1):
            yield start_date + timedelta(n)
    else:
        raise UserError(_("End date %s  is less than the start date %s") % (end_date, start_date))


def get_dates(start_date, end_date, included_days=None):
    list_dates = []
    if included_days is None:
        included_days = [0, 1, 2, 3, 4, 5, 6]
    for dt in daterange(start_date, end_date):
        day_number = int(dt.strftime("%w"))
        if day_number in included_days:
            list_dates.append(dt)
    return list_dates


class RoomTypeAvailability(models.Model):
    _name = BE_MOD_AVAILABILITY
    _description = "Room Type Availability"
    _order = "date, room_type_id"
    _inherit = 'mail.thread'

    @api.depends('max_avail', 'reserved', 'occupied', 'blocked')
    def _compute_availability(self):
        for rec in self:
            unavailable = rec.reserved + rec.occupied + rec.blocked
            rec.real_availability = rec.max_avail - unavailable

    date = fields.Date('Date', required=True, tracking=True, readonly=True)
    room_type_id = fields.Many2one(BE_MOD_ROOM_TYPES, 'Room Type', readonly=True,
                                   required=True, tracking=True,
                                   ondelete='cascade')
    be_hotel_id = fields.Many2one(related='room_type_id.be_hotel_id',store=True)
    hotel_name = fields.Char(related=be_hotel_id.name)
    max_avail = fields.Integer(related="room_type_id.room_count", string="Max. Availability", readonly=True)
    stop_sale = fields.Boolean(string='Stop Sale', default=False)
    quota = fields.Integer("Quota", help='set a value to override the availabity manually', default=0)
    reserved = fields.Integer("Reserved")
    occupied = fields.Integer("Occupied", compute='_compute_avail', store=True)
    blocked = fields.Integer("Blocked", compute='_compute_avail', store=True)
    real_availability = fields.Integer("Availability", compute="_compute_availability", store=True)
    reserved_rooms = fields.Integer("Reserved Rooms", compute="_compute_availability", store=True)


    _sql_constraints = [
        ('be_hotel_id,room_type_date_registry_unique', 'unique(be_hotel_id,room_type_id, date)', 'Only one availability per hotel,day,room type !')
    ]

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, ' %s %s' % (rec.room_type_id.code, rec.date)))
        return res

    @api.model
    def search_availability(self, room_type, date):
        current_avail = self.search([("date", "=", date),
                                     ("room_type_id", "=", room_type.id)], limit=1)
        if not current_avail:
            values = {'date': date,
                      'room_type_id': room_type.id,
                      }
            return self.create(values)
        return current_avail

    def check_room_availabilities(self, rooms, checkin_date, checkout_date):
        dates = get_dates(checkin_date, checkout_date)
        for date in dates:
            for room in rooms:
                room_availability = self.search_availability(room, date)
                if room_availability.real_availability < 1:
                    rooms -= room
        return rooms

    def check_reservation(self, reservation_ids, room_type=False):
        channel_types = ['ota']
        book_engine_types = ['website']

        if room_type:
            room_type_ids = [room_type.id]
        else:
            rec_room_type = self.env[BE_MOD_ROOM_TYPES].search([])
            room_type_ids = rec_room_type.mapped('id')

        availabilities = {}
        for res in reservation_ids:
            for res_line in res.reservation_line:
                for res_price_line in res_line.price_line:
                    channel_qty = book_engine_qty = hotel_qty = 0
                    price = res_price_line.price

                    if res.book_src_type.code in channel_types:
                        channel_qty = res_price_line.qty
                    elif res.book_src_type.code in book_engine_types:
                        book_engine_qty = res_price_line.qty
                    else:
                        hotel_qty = res_price_line.qty

                    # check if room_type is a master room
                    if res_line.room_type.id and res_line.room_type.id in room_type_ids:
                        master_room_type = res_line.room_type.get_master_room()
                        if (master_room_type.id, res_price_line.date) in availabilities:
                            avail = availabilities[(master_room_type.id, res_price_line.date)]
                            channel_qty = avail['channel'] + channel_qty
                            hotel_qty = avail['hotel'] + hotel_qty
                            book_engine_qty = avail['book_engine'] + book_engine_qty
                            price = avail['price'] + price

                        availabilities[(master_room_type.id, res_price_line.date)] = {'channel': channel_qty,
                                                                                      'hotel': hotel_qty,
                                                                                      'book_engine': book_engine_qty,
                                                                                      'price': price
                                                                                      }
        return availabilities
