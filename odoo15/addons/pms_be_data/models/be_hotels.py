from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
PRICE_MODE = [('room', 'Per Room'),
              ('std_occup', 'Standard Occupancy'),
              ('occupancy', 'Per Occupancy'),
              ]



class BeAccomodation(models.Model):
    _name = 'be.hotels'
    _description = 'BE Accommodation'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    @api.depends('room_type_ids.room_count')
    def _compute_total_room(self):
        for rec in self:
            room_count = 0
            for room in rec.room_type_ids:
                room_count += room.room_count
            rec.room_count = room_count

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True,
                                 string='Related Partner', help='Partner-related data of the accomodation')
    code = fields.Char(string="Hotel Code", readonly=True)
    destination = fields.Many2one(related='partner_id.city_id',store=True)
    #accomodation_type_id = fields.Many2one('ota.accomodation.type', string="Type")

    # Accommodation structure
    room_type_ids = fields.One2many('be.room.type','be_hotel_id',string='Room Types',readonly=True)
    room_count = fields.Integer('Total Room', compute="_compute_total_room", readonly=True)

    # amenity_ids = fields.Many2many('ota.accomodation.amenity', string="Amenities")
    # board_ids = fields.Many2many('be.board', string="Boards", required=True)
    price_mode = fields.Selection(PRICE_MODE, string="Price mode", default="room")
    taxes_ids = fields.Many2many('be.taxes', string='Taxes', copy=True)
    arrival_hour = fields.Float(string='Default Arrival Hour (GMT)', help="HH:mm Format", default=12.0)
    departure_hour = fields.Float(string='Default Departure Hour (GMT)', help="HH:mm Format", default=12.0)
    additional_hours = fields.Integer('Additional Hours',
                                      help="Provide the min hours value for \
                                         check in, checkout days, whatever \
                                         the hours will be provided here based \
                                         on that extra days will be calculated.")

    age_1_max = fields.Integer(string="Max First Age")
    age_2_max = fields.Integer(string="Max Second Age")
    age_3_max = fields.Integer(string="Max Third Age")
    reservation_email = fields.Char(string='Reservation Email')
    # reservations infos
    hotel_id = fields.Char(string='Hotel ID',
                           required=True,
                           help="Unique identifier provided by government tourism administration.",
                           )
    rate_plan_ids = fields.One2many('be.rate.plan','be_hotel_id','Rate Plans')

    @api.model
    def get_property_setting(self, accomodation_id, field_name=None):
        property = self.search([('id', '=', accomodation_id)], limit=1)
        if property:
            if not field_name:
                return property
            else:
                if not eval("property.%s" % field_name):
                    raise UserError(_('unknown Property Field Name %s') % field_name)
                else:
                    return eval("property.%s" % field_name)
        else:
            raise UserError(_('No property settings found!! Please configure your property settings'))

    # def view_availabilities_action(self):
    #     action = self.env.ref('ota.action_ota_availability_analysis').read()[0]
    #     action['domain'] = [('accomodation_id', '=', self.id)]
    #     return action

    @api.model
    def create(self, vals):
        # create code for the accomodation
        vals['code'] = self.env['ir.sequence'].next_by_code('ota.accomodation')
        vals['category_id'] = self.partner_id.add_supplier_category('pms_be_data.res_partner_category_accommodation')
        return super(BeAccomodation, self).create(vals)

    def write(self, vals):
        # Add category accommodation if not exist
        vals['category_id'] = self.partner_id.add_supplier_category('pms_be_data.res_partner_category_accommodation')
        return super(BeAccomodation, self).write(vals)

    def get_destination_accomodation_rooms(self,destination=False,be_hotel_id=False):
        if destination:
            domain = [('city_id.name', 'ilike', destination)]
        elif be_hotel_id:
            domain = [('id', '=', be_hotel_id.id)]
        else:
            domain = []
        accommodation_ids = self.env['be.hotels'].search(domain)
        rooms = False
        if accommodation_ids:
            rooms = self.env['be.room.type']
            for hotel in accommodation_ids:
                rooms += hotel.room_type_ids
        return accommodation_ids,rooms








    def search_availability(self, options):
        results = []
        availability_obj = self.env['be.room.type.availability']
        checkin_date = options.get('checkin_date')
        checkout_date = options.get('checkout_date')
        destination = options.get('destination', False)
        partner_id = options.get('partner_id',False)
        currency_id = options.get('currency_id', False)
        adults = options.get('adults', 1)
        childs = options.get('childs', 0)
        babies = options.get('babies', 0)

        accommodation_ids = self.env['be.hotels'].search([('city_id.name', 'ilike', destination.name)])
        if not accommodation_ids:
            return {'success': False,
                    'warning': 'No contract available for this customer on this destination'}

        # search for valid contracts for the selected customer - the web client has several contracts
        rate_plan_ids = accommodation_ids.get_rates(options)
        if not rate_plan_ids:
            return {'success': False,
                    'warning': 'No Rate plan available for this destination'}

        rate_items = rate_plan_ids.get_room_by_occupancy(options)
        room_type_ids = rate_items.mapped('room_type_id')
        room_type_ids = availability_obj.check_room_availabilities(room_type_ids, checkin_date, checkout_date)

        for rate_plan in rate_plan_ids:
            # search for valid rooms in terms of occupancy for found contracts
            rate_items = rate_plan.get_room_by_occupancy(adults, childs, babies)

            # check the availability of the rooms found
            room_type_ids = availability_obj.check_room_availabilities(room_type_ids,checkin_date,checkout_date)
            room_use_ids = room_type_ids.get_room_use_ids(adults, childs, babies)

        # prepare returned results
        options.update({
            'duration': (checkout_date - checkin_date).days,
            'rate_plan_ids': rate_plan_ids,
            'accomodation_ids': accommodation_ids,
            'results': results,
        })
        return options

    def get_rates(self, options):
        rate_plans = self.env['be.rate.plan']
        checkin_date = options.get('checkin_date')
        checkout_date = options.get('checkout_date')
        destination = options.get('destination', False)
        partner_id = options.get('partner_id', False)
        currency_id = options.get('currency_id', False)
        for rec in self:
            domain = [('be_hotel_id', '=', rec.id),
                      ('date_start', '<=', checkin_date),
                      ('date_end', '>=', checkout_date),
                      ('state', '=', 'active'),
                      ('currency_id','=',currency_id)
                      ]
            rate_plans += rate_plans.search(domain)
        return rate_plans