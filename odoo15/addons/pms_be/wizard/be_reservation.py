from datetime import datetime, timedelta
import logging

from odoo import fields, models, api,_
from odoo.addons import decimal_precision as dp

BE_MOD_ACCOMODATION = 'be.hotels'
BE_MOD_AVAILABILITY = 'be.room.type.availability'
BE_MOD_ROOM_TYPES = 'be.room.type'
BE_MOD_MEAL_BORD = 'be.board'
BE_MOD_RATE_PLAN = 'be.rate.plan'
BE_MOD_ROOM_OCCUPANCY = 'be.room.occupancy'

class BeReservation(models.TransientModel):
    _name = 'be.reservation'
    _description = 'Booking engine process'

    @api.onchange('accomodation_ids')
    def onchange_accomodation_ids(self):
        domain = {'domain': {'be_hotel_id': [('id', 'in', self.accomodation_ids.ids)]}}
        return domain

    @api.onchange('rooms')
    def onchange_rooms(self):
        domain = {'domain': {'selected_room': [('id', 'in', self.rooms.ids)]}}
        return domain

    @api.onchange('selected_room')
    def onchange_rooms(self):
        self.room_occupancies_ids = self.selected_room.room_occupancies_ids
        if self.room_occupancies_ids:
            self.selected_occupancy = self.room_occupancies_ids[0]
            self.adults = self.selected_occupancy.adult
            self.childs = self.selected_occupancy.child
            self.babies = self.selected_occupancy.baby

    @api.onchange('selected_room')
    def onchange_rooms(self):
        self.room_occupancies_ids = self.selected_room.room_occupancies_ids

    @api.depends('checkin_date', 'checkout_date')
    def _compute_duration(self):
        for rec in self:
            if rec.checkout_date and rec.checkin_date:
                rec.duration = (rec.checkout_date - rec.checkin_date).days

    @api.depends('adults', 'childs')
    def _get_pax(self):
        for rec in self:
            rec.pax = rec.adults + rec.childs

    def _get_default_currency_id(self):
        return self.env.company.currency_id.id

    @api.depends('reservation_line.subtotal', 'extra_line_ids.subtotal', 'reservation_line.disc_total', 'city_tax')
    def _amount_all(self):
        """
        Compute the total amounts of the reservation.
        """
        rec_taxes = self.env['be.taxes']
        for rec in self:
            amount_subtotal = amount_extra = 0.0
            for line in rec.reservation_line:
                amount_subtotal += line.subtotal
            # Compute City Tax
                # Compute City Tax
                info_city_tax = {}
                if rec.be_hotel_id.taxes_ids:
                    rec.city_tax_ids = rec.be_hotel_id.taxes_ids
                    rec.has_city_tax = True
                    info_city_tax = rec_taxes.get_city_tax_value(rec.city_tax_ids, nights=rec.duration, pax=rec.pax,
                                                                   total_stay=amount_subtotal)
                    rec.city_tax = info_city_tax['amount']
                    exclused_tax = info_city_tax['excluded']


            for extra in rec.extra_line_ids:
                amount_extra += extra.subtotal
            amount_total = amount_subtotal + amount_extra
            if rec.currency != rec.company_currency:
                date = rec.reservation_date and rec.reservation_date.date() or fields.Date.today()
                currency_amount_subtotal = rec.currency._convert(amount_subtotal, rec.company_currency, rec.env.company,
                                                                 date)
                currency_amount_total = rec.currency._convert(amount_total, rec.company_currency, rec.env.company, date)
            else:
                currency_amount_total = amount_total
                currency_amount_subtotal = amount_subtotal
            rec.update({
                'amount_subtotal': amount_subtotal,
                'amount_extra': amount_extra,
                'amount_total': amount_subtotal + amount_extra,
                'currency_amount_subtotal': currency_amount_subtotal,
                'currency_amount_total': currency_amount_total,
                'amount_total_with_taxe': currency_amount_total
            })

    def _get_default_arrival_hour(self):
        if self.be_hotel_id:
            return self.be_hotel_id.arrival_hour

    def _get_default_departure_hour(self):
        if self.be_hotel_id:
            return self.be_hotel_id.departure_hour

    @api.depends('reservation_line')
    def _get_rates(self):
        for rec in self:
            rates = []
            for line in rec.reservation_line:
                rates.append(line.rate.id)
            rec.rate_ids = [(6, 0, rates)]

    def _get_room_counts(self):
        for rec in self:
            rec.room_count = sum(rec.reservation_line.mapped('qty'))

    @api.depends('currency')
    def _get_currency_rate(self):
        for rec in self:
            rates = None
            rate_date = fields.Date.today()
            if rec.currency:
                rates = self.env['res.currency']._get_conversion_rate(rec.currency,
                                                                      self.env.company.currency_id,
                                                                      self.env.company,
                                                                      rate_date)
            rec.exchange_rate = rates or 1


    def _check_cc_info(self):
        for rec in self:
            rec.cc_card = int(rec.cc_info)

    state = fields.Selection([
        ('destination', 'Destination'),
        ('hotels', 'Available hotels'),
        ('hotel', 'Hotel Selection'),
        ('request', 'Booking Request'),
        ('rooms', 'Available Rooms'),
        ('book', 'Room Booking'),
        ('extra', 'Room Booking'),
        ('confirm','Confirmation'),
        ('payment','Payment'),
        ('done', 'Done'),
    ], string='State',
    required=True,
    default='destination')

    reservation_date = fields.Datetime(string='Date', default=fields.Datetime.today())
    checkin_date = fields.Date(string="Checkin")
    checkout_date = fields.Date(string="Checkout")
    adults = fields.Integer(string="Adult", default=1)
    childs = fields.Integer(string="Child", default=0)
    babies = fields.Integer(string="Baby", default=0)
    rooms = fields.Integer(string="Rooms", default=1)
    currency_id = fields.Many2one('res.currency',
                                  string="Currency",
                                  default=_get_default_currency_id,
                                  required=True)

    partner_id = fields.Many2one('res.partner',string="Customer")

    # context many hôtels
    destination = fields.Many2one('res.city', 'Destination')
    # Available hotels for destination
    accomodation_ids = fields.Many2many(BE_MOD_ACCOMODATION,
                                        string="Available Hotels",
                                        readonly=True)
    # Selected hotel
    be_hotel_id = fields.Many2one(BE_MOD_ACCOMODATION,
                                  string="Booked Hotel",
                                  )
    has_city_tax = fields.Boolean(string='City Tax to compute',default=False)

    # Added Fields to manage BE features
    error_message = fields.Text(string='Message')
    state_warning = fields.Boolean(string='Display Warning or Error',default=False)
    rooms = fields.Many2many(BE_MOD_ROOM_TYPES,string='Available rooms',readonly=True)
    selected_room = fields.Many2one(BE_MOD_ROOM_TYPES, string='Hotel available Rooms')
    room_occupancies_ids = fields.One2many(related='selected_room.room_occupancies_ids')
    selected_occupancy = fields.Many2one(BE_MOD_ROOM_OCCUPANCY, string='Selected Occupancy')
    room_number = fields.Integer(string='Room #', default=1)
    result_ids = fields.Many2many('be.result', string="Search Results")
    duration = fields.Integer(string="Nights", compute="_compute_duration", store=True)
    pax = fields.Integer(string="PAX", compute="_get_pax", store=True)

    ######## En Cours de validation

    cancel_date = fields.Date(string='Date cancel', readonly=False, copy=False)
    arrival_time = fields.Float(string="Arrival time", default=_get_default_arrival_hour,
                                states={'cancel': [('readonly', True)]}, help="expected arrival time")
    departure_time = fields.Float(string="Departure time", default=_get_default_departure_hour,
                                  states={'cancel': [('readonly', True)]}, help="expected departure time")
    duration = fields.Integer(string="Nights", compute="_compute_duration", store=True)
    room_count = fields.Integer(string="Rooms", compute="_get_room_counts")
    partner = fields.Many2one('res.partner', string='Main Guest', states={'cancel': [('readonly', True)]})
    partner_country = fields.Many2one(related="partner.country_id", store=True)
    partner_country_image = fields.Char(related="partner.country_id.image_url")
    guest_to_invoice = fields.Many2one('res.partner', string='Guest to invoice',
                                       states={'cancel': [('readonly', True)]})

    adult_number = fields.Integer(string='Adults', default=1, states={'cancel': [('readonly', True)]})
    child_number = fields.Integer(string='Childs', states={'cancel': [('readonly', True)]})
    pax = fields.Integer(string="PAX", compute="_get_pax", store=True)
    total_deposit_amount = fields.Float(digits='Product Price')

    reservation_line = fields.One2many('be.reservation.line', 'reservation',
                                       string='Reservation lines', readonly=True,
                                       states={'draft': [('readonly', False)],
                                               'sent': [('readonly', False)]
                                               })

    extra_line_ids = fields.One2many('be.reservation.extra', 'reservation_id',
                                     string='Reservation Extra lines', readonly=True,
                                     states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    guest_note = fields.Text(string="Guest Note", states={'cancel': [('readonly', True)]}, copy=False)
    note = fields.Text(string="Internal Note", copy=False)

    city_tax = fields.Float(compute='_amount_all', store=True)
    rate_ids = fields.Many2many("be.rate.plan", compute='_get_rates', string="Rates", readonly=True, store=True)
    currency = fields.Many2one("res.currency", compute='_set_currency', string="Currency", readonly=True, store=True)
    company_currency = fields.Many2one("res.currency", string="Company Currency",
                                       default=lambda self: self.env.company.currency_id)
    exchange_rate = fields.Float(string='Exchange Rate', compute="_get_currency_rate", digits=(4, 6), store=True)

    amount_subtotal = fields.Float(string='Subtotal', digits='Product Price',
                                   store=True, readonly=True, compute='_amount_all', tracking=True)
    amount_extra = fields.Float(string='Extra', digits='Product Price',
                                store=True, readonly=True, compute='_amount_all', tracking=True)
    amount_total = fields.Float(string='Total', digits='Product Price',
                                store=True, readonly=True, compute='_amount_all', tracking=True)
    currency_amount_subtotal = fields.Float(string='Subtotal in currency', digits='Product Price',
                                            store=True, readonly=True, compute='_amount_all', tracking=False)
    currency_amount_total = fields.Float(string='Total in currency', digits='Product Price',
                                         store=True, readonly=True, compute='_amount_all', tracking=True)
    amount_total_with_taxe = fields.Float(string='Total + Tax', digits='Product Price',
                                          store=True, readonly=True, compute='_amount_all', tracking=True)


    # TODO: to better manage credit card informations
    cc_id = fields.Many2one('be.reservation.cc', string="Credit Card")
    # garantie
    cc_info = fields.Boolean()
    cc_card = fields.Integer(compute="_check_cc_info", string="Credit card")
    cc_number = fields.Char(string='Number')
    cc_owner = fields.Char(string='Holder')
    cc_type = fields.Char(string='Type CCARD')
    cc_expiring = fields.Char('Expiration')
    cc_cvv = fields.Char('CCV')

    def dummy(self):
        return True

    def search_availability(self,options):
        availability_obj = self.env[BE_MOD_AVAILABILITY]
        destination = options.get('destination',False)
        # adults = options.get('adults',1)
        # childs = options.get('childs',0)
        # babies = options.get('babies',0)
        checkin_date = options.get('checkin_date')
        checkout_date = options.get('checkout_date')
        # search according accommodations
        accomodation_ids,rooms = self.env[BE_MOD_ACCOMODATION].get_destination_accomodation_rooms(destination.name)
        if not rooms:
            options.update(
                {
                 'success': False,
                 'warning': 'No available rooms for this customer on this destination %s' % destination.name
                }
            )
            return options

        # Filter according requested occupation
        rooms = rooms.get_room_by_occupancy(adults, childs, babies)
        logging.info('filtered rooms %s' % rooms)

        logging.info('filtered rooms %s' % rooms)
        room_occupancies = rooms.get_room_occupancy_ids(adults, childs, babies)
        logging.info('filtered room_occupancies %s' % rooms)
        rooms_rates = self.env['be.rate.plan'].get_occupancy_prices(room_occupancies,checkin_date,checkout_date)
        logging.info('get_rooms_rates %s' % rooms_rates)
        self.result_ids = rooms_rates

        vals = {
            'room_rates': self.group_values(self.result_ids.sorted(key=lambda r: r.price)),
            'checkin_date': self.checkin_date,
            'checkout_date': self.checkout_date,
            'duration': (self.checkout_date - self.checkin_date).days,
            'adults': self.adults,
            'childs': self.childs,
            'room_count': self.rooms
        }
        return vals

    def search_destination(self):
        availability_obj = self.env[BE_MOD_AVAILABILITY]
        self.error_message = ''
        state_warning = False
        accomodation_ids, rooms = self.env[BE_MOD_ACCOMODATION].get_destination_accomodation_rooms(destination=self.destination.name)
        if not rooms:
            self.error_message = 'No available rooms for this customer on this destination %s' % self.destination.name
            state_warning = True
            return self.get_action('destination')
        self.accomodation_ids = accomodation_ids
        self.be_hotel_id = accomodation_ids[0]
        self.rooms = availability_obj.check_room_availabilities(rooms, self.checkin_date, self.checkout_date)
        return self.get_action('hotels')

    def search_hotel(self):
        availability_obj = self.env[BE_MOD_AVAILABILITY]
        self.error_message = ''
        state_warning = False
        accomodation_ids, rooms = self.env[BE_MOD_ACCOMODATION].get_destination_accomodation_rooms(
            be_hotel_id = self.be_hotel_id)
        if not rooms:
            self.error_message = 'No available rooms for this customer on this destination %s' % self.destination.name
            state_warning = True
            return self.get_action('destination')
        self.accomodation_ids = accomodation_ids
        self.rooms = availability_obj.check_room_availabilities(rooms, self.checkin_date, self.checkout_date)
        if self.rooms:
            self.selected_room = self.rooms[0]

        return self.get_action('request')

    def hotel_add_room(self):

        return self.get_action('request')

    def validate(self):
        options = {
            'checkin_date': self.checkin_date,
            'checkout_date': self.checkout_date,
            'destination': self.destination,
            'partner_id': self.partner_id,
            'partner_currency': self.currency_id,
            'adults': self.adults,
            'childs': self.childs,
            'babies': self.babies,
            'success': True,
            'warning': '',
        }
        self.search_availability(options)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Result',
            'res_model': 'be.result',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.result_ids.ids)],
            'context': {'search_default_group_by_room_type_id': 1,
                        'search_default_group_by_rate_id': 1,
                        'search_default_group_by_board_id': 1
                        },
            'target': 'current',
        }

    @staticmethod
    def group_values(records):
        """ this function groups the records for easier use in
             the frontend template of the booking search results:
            [
                {
                    'room' : room,
                    'rates':[
                        {'rate': rate,
                         'boards':[
                                {'board': board,
                                 'items': recordset of prices
                                 }
                             ]
                         }

                    ]
                }
            ]

            :param records: recordset
            :return: list of dicts
        """
        results = []
        if records:
            rooms = records.mapped('room_type_id')
            for room in rooms:
                room_vals = {
                    'room': room,
                    'rates': []
                }
                rates = records.filtered(lambda r: r.room_type_id == room).mapped('rate_plan_id')
                for rate in rates:
                    rate_vals = {
                        'rate': rate,
                        'boards': []
                    }
                    boards = records.filtered(lambda r: r.room_type_id == room and
                                                        r.rate_plan_id == rate
                                              ).mapped('board_id')
                    for board in boards:
                        items = records.filtered(lambda r: r.room_type_id == room and
                                                           r.rate_plan_id == rate and
                                                           r.board_id == board
                                                 )
                        board_vals = {
                            'board': board,
                            'items': items,
                        }
                        rate_vals['boards'].append(board_vals)

                    room_vals['rates'].append(rate_vals)
                    room_vals['availability'] = min(items.mapped('availability'))

                room_vals['price_from'] = sum(room_vals['rates'][0]['boards'][0]['items'].mapped('price'))
                results.append(room_vals)

        return results




    def get_action(self, state, ctx=None):
        self.state = state
        action = {
            'name': _('BE Reservation Wizard '),
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }
        return action

class BeReservationLine(models.TransientModel):
    _name = 'be.reservation.line'
    _description = 'BE reservation line'

    @api.depends('price_line.subtotal')
    def _amount_all(self):
        for rec in self:
            rec.subtotal = sum(line.subtotal for line in rec.price_line)
            rec.childrens_number = rec.child_first_age + rec.child_second_age + rec.child_third_age
            rec.extra_beds = sum(line.extra_beds for line in rec.price_line)
            rec.disc_total = sum(line.discount for line in rec.price_line)
            rec.total_tax = sum(line.total_tax for line in rec.price_line)

    @api.depends('adults_number', 'child_first_age', 'child_second_age', 'child_third_age', 'adult_extra_bed', 'qty')
    def _get_pax(self):
        for rec in self:
            rec.occupancy = str(rec.adults_number + rec.adult_extra_bed) + '/' + str(rec.childrens_number)
            rec.pax = (rec.adults_number + rec.childrens_number + + rec.adult_extra_bed) * rec.qty

    def _get_room_counts(self):
        for rec in self:
            rec.room_count = rec.qty


    reservation = fields.Many2one('be.reservation', string="Reservation", ondelete='cascade')
    state = fields.Selection(related='reservation.state')
    checkin_date = fields.Date(related='reservation.checkin_date')
    checkout_date = fields.Date(related='reservation.checkout_date')
    duration = fields.Integer(related='reservation.duration')
    name = fields.Text(string='Name', help="Description")
    room_type = fields.Many2one(BE_MOD_ROOM_TYPES, string="Room type", required=True)
    rate = fields.Many2one(BE_MOD_RATE_PLAN, string="Rate", required=True)
    board_type = fields.Many2one(BE_MOD_MEAL_BORD, string="Board type", required=True)
    occupancy_id = fields.Many2one(BE_MOD_ROOM_OCCUPANCY, string="Occupancy", required=True)
    product_id = fields.Many2one('product.product', string="Product")  # compute='_get_board_room_product', store=True
    # changed qty to integer
    qty = fields.Integer('Room qty', default=1, required=True, help="Room quantity")
    price_line = fields.One2many('be.reservation.line.price', 'reservation_line', string='Price line')
    subtotal = fields.Float('Subtotal', digits='Product Price', compute='_amount_all', store=True)
    disc_total = fields.Float('Discount Total', digits='Product Price', compute='_amount_all',
                              store=True)

    extra_beds = fields.Float('Extra-Beds',
                              digits='Product Price',
                              compute='_amount_all',
                              store=True)
    adults_number = fields.Integer('Adults/Room', default=1)
    childrens_number = fields.Integer('Children/Room', compute='_amount_all', store=True)
    occupancy = fields.Char(string="Occup./Room", compute="_get_pax", store=True)
    pax = fields.Integer(string="PAX", compute="_get_pax", store=True)
    child_first_age = fields.Integer(string='Child in First Age')
    child_second_age = fields.Integer(string='Child in Second Age')
    child_third_age = fields.Integer(string='Child in Third Age')
    adult_extra_bed = fields.Integer(string='Adult Extra Beds')
    room_count = fields.Integer(string="Rooms", compute="_get_room_counts")
    # --- Reservation tax support
    total_tax = fields.Float(compute='_amount_all', digits='Product Price',
                             string='Total Tax', readonly=True, store=True)

    def compute_days(self):
        for rec in self:
            temp_date = rec.checkin_date
            night = 0
            # delete all price records
            rec.price_line = [(6, 0, [])]
            day_pricing = []
            while temp_date < rec.checkout_date:
                night += 1
                rate_price = rec.rate.get_room_price(temp_date,
                                                     rec.room_type,
                                                     rec.board_type,
                                                     rec.occupancy_id,
                                                     )

                vals = {'reservation_line': rec.id,
                        'date': temp_date,
                        'board_type': rec.board_type.id,
                        'board_type': rec.occupancy_id.id,
                        'qty': rec.qty,
                        'rate_price': rate_price,
                        'price': rate_price,
                        'night': night,
                        'percent_discount': 0.00,
                        'discount': 0.00,
                        }
                day_pricing.append((0, 0, vals))
                temp_date = temp_date + timedelta(days=1)
            rec.price_line = day_pricing


class BeReservationLinePrice(models.TransientModel):
    _name = 'be.reservation.line.price'
    _description = 'BE reservation line price'

    def compute_extra_beds(rec):
        rec_ebed = rec.env['be.price.extra.beds']
        day_extra_room_beds = 0
        rec.qty = rec.reservation_line.qty
        for range_type, age_range in [('first', rec.reservation_line.child_first_age),
                                      ('second', rec.reservation_line.child_second_age),
                                      ('third', rec.reservation_line.child_third_age)
                                      ]:
            if age_range < 0:
                age_range = 0

            day_extra_room_beds += rec_ebed.get_price_range_type(rec.reservation_line.rate,
                                                                 range_type,
                                                                 rec.date,
                                                                 age_range,
                                                                 rec.price,
                                                                 rec.reservation_line.room_type,
                                                                 rec.board_type)
        return  day_extra_room_beds


    @api.depends('qty', 'rate_price', 'price', 'extra_beds')
    def compute_price_line(self):
        rec_prod_template = self.env['product.template']
        for rec in self:
            rec.extra_beds = 0 # rec.compute_extra_beds(rec)
            if (rec.rate_price - rec.price) > 0 and rec.rate_price > 0 and not rec.reservation_line.promotion_id:
                rec.percent_discount = (rec.rate_price - rec.price) / rec.rate_price * 100
            else:
                rec.percent_discount = 0
            # Fall back to rate_price if price is 0
            if rec.price == 0:
                rec.price = rec.rate_price

            discount = (rec.rate_price - rec.price) * rec.reservation_line.qty
            rec.discount = discount if discount > 0 else 0
            rec.net_price = rec.price + rec.extra_beds
            rec.subtotal = rec.net_price * rec.reservation_line.qty
            # reservation tax support
            product_id = rec_prod_template.get_accomodation_product(rec.reservation_line.room_type,
                                                                    board=rec.board_type)
            rec.tax_ids = [(6, 0, product_id.taxes_id.ids)]
            taxes = rec.tax_ids.compute_all(rec.net_price, rec.reservation.currency, rec.qty,
                                            product=product_id, partner=rec.reservation.partner)
            rec.total_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))

    @api.depends('reservation.state')
    def link_availability(self):
        rec_avail = self.env[BE_MOD_AVAILABILITY]
        for rec in self:
            if rec.reservation.state in ('draft', 'confirmed', 'done'):
                day_availability = rec_avail.search_availability(rec.room_type_id, rec.date)
                rec.room_availability_id = day_availability.id

    reservation_line = fields.Many2one('be.reservation.line', string="Reservation line", ondelete='cascade')
    reservation = fields.Many2one(related='reservation_line.reservation')
    reservation_state = fields.Selection(related='reservation.state')
    room_type_id = fields.Many2one(related='reservation_line.room_type')
    date = fields.Date(string='Date')
    room_availability_id = fields.Many2one(BE_MOD_AVAILABILITY, compute='link_availability', store=True)
    availability = fields.Integer(related='room_availability_id.real_availability')
    board_type = fields.Many2one(BE_MOD_MEAL_BORD, string="Board type")
    qty = fields.Integer(string='Quantity')
    rate_price = fields.Float(string='Rate Price', digits='Product Price')
    price = fields.Float('Price')
    extra_beds = fields.Float('Extra-Beds', digits='Product Price')
    percent_discount = fields.Float(string='Discount(%)', compute='compute_price_line', store=True,
                                    digits='Product Price')
    discount = fields.Float(string='Discount', compute='compute_price_line', store=True, digits='Product Price')
    net_price = fields.Float('Net Price', digits='Product Price')
    subtotal = fields.Float('Subtotal', compute='compute_price_line', store=True, digits='Product Price')
    night = fields.Integer(string='Night', readonly=True)

    # Reservation Tax support
    tax_ids = fields.Many2many('account.tax', string='Taxes', compute='compute_price_line', store=True)
    total_tax = fields.Float(compute='compute_price_line', digits='Product Price',
                             string='Total Tax', readonly=True, store=True)



PRICE_MODE_SELECTION = [('night', 'Night / Qty'),
                        ('person', 'Per Person'),
                        ('stay', 'Per Stay'),
                        ('person_night', 'Person / Night'),
                        ('person_night_qty', 'Night / Person / Qty'),
                        ('person_stay', 'Person / Stay'),
                        ('percent', 'Percentage'),
                        ('free', 'Free'),
                        ('room', 'Per Room'),
                        ('week', 'Per Week'),
                        ('person_week', 'Person / Week'),
                        ('room_week', 'Room / Week'),
                        ('total_stay', 'Percentage on total stay'),
                        ('resa', 'Per Reservation'), ]

class BeReservationExtra(models.TransientModel):
    _name = 'be.reservation.extra'
    _description = 'Reservation extra line'

    reservation_id = fields.Many2one('be.reservation', string="Reservation", ondelete='cascade')
    name = fields.Char(string='Description')
    product_id = fields.Many2one('product.product', string="Product")
    date = fields.Date(string='Date')
    price_mode = fields.Selection(PRICE_MODE_SELECTION, string='Price mode')
    unit_price = fields.Float('Unit Price', digits='Product Unit of Measure')
    nights = fields.Integer('Nights', help="number of nights")
    persons = fields.Integer('Persons', help="number of persons")
    qty = fields.Float('Quantity', digits='Product Unit of Measure', default=1)
    computed_qty = fields.Float(compute="_compute_qty", digits='Product Price', store=True)
    subtotal = fields.Float('Subtotal', compute="_compute_total", digits='Product Price', store=True)
    # Reservation Tax support
    tax_ids = fields.Many2many('account.tax', string='Taxes', compute='_compute_total', store=True)
    total_tax = fields.Float(compute='_compute_total', digits='Product Price',
                             string='Total Tax', readonly=True, store=True)

    @api.depends('price_mode', 'nights', 'persons', 'qty')
    def _compute_qty(self):
        for rec in self:
            if rec.price_mode == 'person_night':
                rec.computed_qty = rec.persons * rec.nights
            elif rec.price_mode == 'person':
                rec.computed_qty = rec.persons
            elif rec.price_mode == 'night':
                rec.computed_qty = rec.nights * rec.qty
            elif rec.price_mode == 'person_night_qty':
                rec.computed_qty = rec.persons * rec.nights * rec.qty
            else:
                rec.computed_qty = 1


    @api.depends('unit_price', 'computed_qty')
    def _compute_total(self):
        for rec in self:
            rec.subtotal = rec.unit_price * rec.computed_qty
            rec.tax_ids = [(6, 0, rec.product_id.taxes_id.ids)]
            taxes = rec.tax_ids.compute_all(rec.unit_price, rec.reservation_id.currency, rec.qty,
                                            product=rec.product_id, partner=rec.reservation_id.partner)
            rec.total_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))

    @api.onchange('price_mode')
    def _price_mode_change(self):
        if self.price_mode == 'person':
            self.nights = 0
        if self.price_mode == 'night':
            self.persons = 0
        self._compute_total()

# TODO: to better manage credit card informations
class BeReservationCC(models.Model):
    _name = 'be.reservation.cc'
    _description = 'Pms Reservation CC'
    _rec_name = "cc_owner"

    cc_info = fields.Boolean()
    cc_number = fields.Char(string='Number')
    cc_owner = fields.Char(string='Holder')
    cc_type = fields.Char(string='Type')
    cc_expiring = fields.Char(string='Expiration')
    cc_cvv = fields.Char(string='CCV')

class BeBookingResult(models.TransientModel):
    _name = 'be.result'
    _description = 'Booking engine search result'

    room_type_id = fields.Many2one('be.room.type', string="Room type")
    date = fields.Date('Date')
    rate_plan_id = fields.Many2one('be.rate.plan', string="Rate")
    board_id = fields.Many2one('be.board', string="Board Service")
    price = fields.Float('Price', digits=dp.get_precision('Product Price'))
    currency_id = fields.Many2one(related='rate_plan_id.currency_id')
    rule = fields.Char(string="Rule", compute="_get_rule")
    availability = fields.Integer(string="Availability")

    @api.depends('rate_plan_id')
    def _get_rule(self):
        for rec in self:
            if rec.rate_plan_id.parent_rate_plan:
                rate_rules = rec.rate_plan_id.get_rules()['rules'][-1]
                rec.rule = '%s ( %s %s)' % (rec.rate_plan_id.parent_rate_plan.name, rate_rules[1], rate_rules[0])

