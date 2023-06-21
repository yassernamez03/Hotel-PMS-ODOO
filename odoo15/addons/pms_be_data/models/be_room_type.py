from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

BE_MAX_OCCUPANCY = 12
BE_STD_OCCUPANCY = 2
BE_MIN_ADULT = 1
BE_MAX_ADULT = 3
BE_MIN_CHILD = 0
BE_MAX_CHILD = 2
BE_MIN_BABY = 0
BE_MAX_BABY = 1


class BeRoomType(models.Model):
    _name = "be.room.type"
    _description = "BE Room Type"
    _order = "sequence,code, name"

    # Used for activate records
    active = fields.Boolean('Active',
                            default=True,
                            help="The active field allows you to hide the \
                            room_type without removing it.")
    # Used for ordering
    sequence = fields.Integer('Sequence', default=0)
    name = fields.Char('Name', required=True)
    code = fields.Char('code', size=8, required=True)
    be_hotel_id = fields.Many2one('be.hotels',
                                  string='Accommodation',
                                  required=True,
                                  ondelete='cascade')
    price_mode = fields.Selection(related='be_hotel_id.price_mode', store=True)
    min_occupancy = fields.Integer('Min Occupancy',
                                   default=1,
                                   help='The minimum guests that room will accept.')
    max_occupancy = fields.Integer('Max Occupancy',
                                   default=BE_STD_OCCUPANCY,
                                   help='The maximum guests that room will accept.')
    min_adult = fields.Integer('Minimum Adult',
                               help="Minimum number of adults",
                               default=BE_MIN_ADULT,
                               )
    max_adult = fields.Integer('Maximum Adult',
                               help="Maximum number of adults",
                               default=BE_MAX_ADULT,
                               )
    min_child = fields.Integer('Minimum Child',
                               help="Minimum number of childrens",
                               default=BE_MIN_CHILD,
                               )
    max_child = fields.Integer('Maximum Child',
                               help="Max number of childrens",
                               default=BE_MAX_CHILD,
                               )
    min_baby = fields.Integer('Minimum Baby',
                              help="Minimum number of Babies",
                              default=BE_MIN_BABY,
                              )
    max_baby = fields.Integer('Maximum Baby',
                              help="Max number of Babies",
                              default=BE_MAX_BABY,
                              )

    price_adult = fields.Float('Default Price Adult', help='Default Price Adult')
    price_child = fields.Float('Default Price Child', help='Default Price Child')
    price_baby = fields.Float('Default Price Baby', help='Default Price Baby')
    supplement_price = fields.Float('Supplement', help='Supplement Price')
    default_board = fields.Many2one("be.board", string='Default Meal Board')
    room_occupancies_ids = fields.One2many('be.room.occupancy', 'room_type_id', string='Room Occupancies')
    exclude_baby = fields.Boolean('Exclude Babies', default=True)
    # total number of rooms in this type
    room_count = fields.Integer('Rooms')
    default_availability = fields.Integer('Default_availability', default=lambda self: self.room_count)

    _sql_constraints = [('code_unique', 'unique(code)',
                         'code must be unique!')]

    def name_get(self):
        res = []
        for room_type in self:
            res.append((room_type.id,
                        ' [%s] %s' % (room_type.code, room_type.name)))
        return res

    def get_room_with_capacity(self, capacity=1):
        room_list = []
        for rec in self:
            if rec.min_occupancy >= capacity and rec.max_occupancy <= capacity:
                room_list.append(rec)
        return room_list

    @api.model
    def get_room_default_price(self, room_occupancy=False):
        room_price = self.price_adult + self.price_child + self.price_baby + self.supplement_price
        if room_occupancy:
            room_price = room_occupancy.get_room_occupancy_price()
        return room_price

    def generate_room_occupancy(self):
        all_uses = []
        self.room_occupancies_ids.unlink()
        for adult in range(self.min_adult, self.max_adult + 1):
            for child in range(self.min_child, self.max_child + 1):
                for baby in range(self.min_baby, self.max_baby + 1):
                    capacity = adult + child
                    if not self.exclude_baby:
                        capacity += baby

                    if self.max_occupancy >= capacity >= self.min_occupancy:
                        all_uses.append((adult, child, baby))

        rec_room_occupancy = self.env['be.room.occupancy']
        for use in all_uses:
            adult, child, baby = use[0], use[1], use[2]
            rec_room_occupancy.create(
                {
                    'adult': adult,
                    'child': child,
                    'baby': baby,
                    'room_type_id': self.id,
                }
            )

    @api.constrains('min_adult', 'max_adult', 'min_child',
                    'max_child', 'min_baby', 'max_baby',
                    'min_occupancy', 'max_occupancy')
    def check_occupancies(self):
        for rec in self:
            if  not (1 <= rec.min_adult <= rec.max_adult
                    and 0 <= rec.min_child <= rec.max_child \
                    and 0 <= rec.min_baby <= rec.max_baby \
                    and not 1 <= rec.min_occupancy <= rec.max_occupancy):
                UserError(_('Min Occupancy must equal or lower than Max Occupancy '))

    def get_room_by_occupancy(self, adults, childs, babies):
        room_types = self.env['ota.accomodation.room.type']
        for rec in self:
            if rec.min_adult <= adults and rec.min_child <= childs:
                if rec.exclude_baby:
                    room_types |= rec
                else:
                    if rec.min_baby <= babies:
                        room_types |= rec
        return room_types

    def get_room_occupancy_ids(self, adults, childs, babies):
        room_occupancies_ids = self.env['be.room.occupancy']
        for rec in self:
            for room_occupancy in rec.room_occupancies_ids:
                if room_occupancy.adult >= adults and room_occupancy.child >= childs:
                    if rec.exclude_baby:
                        room_occupancies_ids |= room_occupancy
                    else:
                        if room_occupancy.baby >= babies:
                            room_occupancies_ids |= room_occupancy
        return room_occupancy


class BeRoomOccupancy(models.Model):
    _name = "be.room.occupancy"
    _description = "BE Room Occupancies"

    @api.depends('adult', 'child', 'baby', 'code')
    def compute_all(self):
        for rec in self:
            code = rec.code
            if not rec.code:
                code = ' '
            rec.name = '%s %sA-%sC-%sB' % (code, rec.adult, rec.child, rec.baby)
            rec.occupancy_code = '%s-%s-%s' % (rec.adult, rec.child, rec.baby)
            rec.number_guests = rec.get_capacity()

    name = fields.Char(string='Room Use', compute='compute_all', store=True)
    code = fields.Char('Code')
    occupancy_code = fields.Char(string='Code Room Use', compute='compute_all', store=True)
    room_type_id = fields.Many2one('be.room.type', 'Room Type')
    adult = fields.Integer('Adults Number', required=True)
    child = fields.Integer('Childs Number', required=True)
    baby = fields.Integer('Babies Number', required=True)
    number_guests = fields.Integer('Number Of Guests', compute='compute_all', store=True)
    is_default = fields.Boolean(string='Default Room Use', default=False)

    def get_capacity(self):
        capacity = self.adult + self.child
        if not self.room_type_id.exclude_baby:
            capacity += self.baby
        return capacity

    def get_room_occupancy_price(self):
        if self.room_type_id.price_mode == 'room':
            price = self.room_type_id.price_adult + self.room_type_id.price_child \
                                       + self.room_type_id.price_baby + self.room_type_id.supplement_price
        else:
            price = self.room_type_id.supplement_price + (
                        self.room_type_id.price_adult * self.adult) + (
                                               self.room_type_id.price_child * self.child) + (
                                               self.room_type_id.price_baby * self.price_baby)
        return price
