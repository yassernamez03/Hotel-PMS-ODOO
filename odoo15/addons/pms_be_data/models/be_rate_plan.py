from odoo import api, fields, models, tools, _
from datetime import timedelta
from odoo.exceptions import ValidationError, UserError

import logging


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


class BeRatePlan(models.Model):
    _name = "be.rate.plan"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "BE Rate Plan"

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('code', size=8, required=True)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean('Active',
                            default=True,
                            help="If unchecked, it will allow you to hide the Rate Plan without removing it.")
    currency_id = fields.Many2one('res.currency', 'Currency', default=_get_default_currency_id, required=True)
    board_type = fields.Many2many('be.board', string="Board")
    be_hotel_id = fields.Many2one('be.hotels',
                                  string='Accommodation',
                                  required=True,
                                  ondelete='cascade')
    partner_ids = fields.Many2many('res.partner',
                                   relation='be_partner_plist',
                                   column1='plist_id',
                                   column2='partner_id',
                                   string="Associated Partners")
    item_ids = fields.One2many(
        'be.rate.plan.item',
        'rate_plan_id',
        string='Rate Plan Items',
        copy=True)
    date_start = fields.Date('From', required=True)
    date_end = fields.Date('To', required=True)

    def name_get(self):
        return [(rate_plan.id, '%s (%s)' % (rate_plan.name, rate_plan.currency_id.name)) for rate_plan in self]

    def price_exchange(self, price, date, from_cur, to_cur):
        # exchange price value according to request currency
        change_price = price
        if to_cur and to_cur != from_cur:
            change_price = from_cur._convert(price,
                                             to_cur,
                                             self.env.user.company_id,
                                             date,
                                             round=False)
        return change_price

    def get_room_price(self, date, room_type, board_type):
        self.ensure_one()
        if self.is_mono_board:
            if board_type != self.board_type:
                return False
        rate_price = self.compute_room_price_rule(date, room_type, board_type)
        # logging.info('## get_room_price Rate > %s, %s, %s,' % (room_type.name, board_type.name, rate_price))
        return rate_price

    def compute_room_price_rule(self, date, room_type, bord_type, occupancy):
        item = self.item_ids.filtered(
            lambda pi: pi.date == date and pi.room_type_id == room_type and pi.occupancy_id == occupancy)
        if item:
            return item.price

    def show_rate_items(self):
        domain = [('id', 'in', self.item_ids.ids)]

        action = {'type': 'ir.actions.act_window',
                  'domain': domain,
                  'views': [(False, 'tree'), (False, 'form'), (False, 'pivot')],
                  'name': _('Prices'),
                  'res_model': 'be.rate.plan.item'}
        return action

    def check_validity(self, checkin_date, checkout_date, reservation_date=False):
        self.ensure_one()
        if not reservation_date:
            reservation_date = fields.Date.today()
        duration = (checkout_date - checkin_date).days
        days_before_checkin = (checkin_date - reservation_date).days
        if duration < self.days_minimum_stay:
            return 'The duration of the stay to book %s, is less than the minimum duration %s ' % (
                duration, self.days_minimum_stay)
        if days_before_checkin < self.days_before_checkin:
            return 'The number of days before check-in %s, is less than the minimum required %s' % (
                days_before_checkin, self.days_before_checkin)
        return True

    def get_hotel_room_types(self):
        domain = [
            ('be_hotel_id', '=', self.be_hotel_id.id)
        ]
        return self.env['be.room.type'].search(domain)

    def generate_prices(self):
        list_dates = get_dates(self.date_start, self.date_end)
        room_type_ids = self.get_hotel_room_types()
        col_items = []
        for day in list_dates:
            for room_type in room_type_ids:
                for occupancy in room_type.room_occupancies_ids:
                    price = room_type.get_room_default_price(room_occupancy=occupancy)
                    vals = {
                        'name': '%s-%s-%s-%s' % (day, room_type.code, self.board_type.code, occupancy.code),
                        'rate_plan_id': self.id,
                        'date': day,
                        'board_id': self.board_type.id,
                        'room_type_id': room_type.id,
                        'occupancy_id': occupancy.id,
                        'price': price,
                    }
                    col_items.append((0, 0, vals))
        return col_items

    def update_prices(self):
        self.item_ids.unlink()
        col_items = self.generate_prices()
        self.item_ids = col_items

    def get_room_by_occupancy(self, available_rooms, checkin_date, checkout_date, adults, childs):
        rate_items = self.env['be.rate.plan.item']
        for rec in self:
            # available rooms to sale
            items = rec.items.filtered(lambda ri: ri.adult >= adults and
                                                  ri.child >= childs and
                                                  checkin_date <= ri.date <= checkout_date
                                                  and ri.room_type.id in available_rooms.ids)
            rate_items += items

        return rate_items

    def get_occupancy_prices(self, room_occupancies, date_checkin, date_checkout):
        rec_item = self.env['be.rate.plan.item']
        domain = [
            ('occupancy_id', 'in', room_occupancies.ids),
            ('active', '=', True),
            ('date', '>=', date_checkin),
            ('date', '<=', date_checkout),
        ]
        item_ids = rec_item.search(domain)
        return item_ids


class BeRatePlanItem(models.Model):
    _name = "be.rate.plan.item"
    _description = "BE Rate Plan Items"

    name = fields.Char('Price Name', help="Explicit rule name for this Rateline.")
    rate_plan_id = fields.Many2one('be.rate.plan', 'Rate Plan', index=True, ondelete='cascade')
    be_hotel_id = fields.Many2one(related='rate_plan_id.be_hotel_id',store=True)
    active = fields.Boolean(related='rate_plan_id.active', store=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        readonly=True, related='rate_plan_id.currency_id', store=True)
    date = fields.Date('Date', help="Starting date for the rate plan item validation")
    price = fields.Float('Price', digits='Product Price')
    board_id = fields.Many2one('be.board', 'Board Service')
    room_type_id = fields.Many2one('be.room.type', 'Room Type')
    occupancy_id = fields.Many2one('be.room.occupancy', string='Occupancy')
    occupancy_code = fields.Char(related='occupancy_id.occupancy_code', store=True)
    adult = fields.Integer(related='occupancy_id.adult', store=True)
    child = fields.Integer(related='occupancy_id.child', store=True)
    baby = fields.Integer(related='occupancy_id.baby', store=True)

    _sql_constraints = [
        ('date_room_type_id_occupancy_id_board_id_rate_plan_id_uniq',
         'unique(date, room_type_id, occupancy_id,board_id, rate_plan_id)',
         'You can not define multiple prices for the same date, board and room type'),
    ]
