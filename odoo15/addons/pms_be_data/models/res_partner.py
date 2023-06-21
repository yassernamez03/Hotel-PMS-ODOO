from odoo import fields, models, api,_

OTA_DOC_TYPES = [('nat_card', 'ID Card'),
                 ('pass', 'Passport'),
                 ('resid', 'Resident Card'),
                 ('driver', "Driver's License"),
                 ]

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            self.zip = self.city_id.zipcode
            self.state_id = self.city_id.state_id
            self.district = False
    district = fields.Many2one('res.city.district', string="District")
    rate_ids = fields.Many2many('be.rate.plan',
                                string="Associated Pricing List")

    birth_date = fields.Date(string='Date of Birth')
    place_of_birth = fields.Char('Place of Birth')
    title = fields.Char('Title')
    name = fields.Char('Name')
    age = fields.Integer('Age')
    country_of_birth = fields.Many2one('res.country', string="Country of Birth")
    # book_src_type = fields.Many2one('ota.source.booking', string="Booking Source Type")
    #
    # default_invoicing_mode_id = fields.Many2one('ota.support.mode', string="Default Support mode",
    #                                             help='Default Support mode for this partner, used by default in reservations')

    doc_type = fields.Selection(OTA_DOC_TYPES, string='Document Type', required=True,
                                help=_('Identity Document Type '), default='nat_card')
    doc_num_id = fields.Char(string='Document Number')
    doc_entry_id = fields.Char(string='Id.Entry', help=_('Id Entry on the territory '))
    doc_expire_date = fields.Date(string='Document Expire Date', help=_('Document Expiration date'))
    doc_country = fields.Many2one('res.country', string="Origin Country",
                                  help=_("Country of origin of the document"))
    doc_authority = fields.Char(string='Authority Name', help=_("Authority issuing the document"))

    #reservation_count = fields.Integer('Reservations', compute="_count_reservations", store=False)
    # TODO activate reservation_ids
    # reservation_ids = fields.One2many('ota.reservation', 'partner', string="Reservations")
    # TODO activate origin
    #origin_reservation_ids = fields.One2many('ota.reservation', 'origin', string="Reservations")
    comm = fields.Float("Commission")


    # TODO activate
    # @api.depends('reservation_ids', 'origin_reservation_ids')
    # def _count_reservations(self):
    #     for rec in self:
    #         if rec.book_src_type.code == 'OTA':
    #             rec.reservation_count = len(rec.origin_reservation_ids)
    #         else:
    #             rec.reservation_count = len(rec.reservation_ids)
    #
    # def view_reservations(self):
    #     action = self.env.ref('ota.action_reservation_window').read()[0]
    #     action['domain'] = ['|',
    #                         ('id', 'in', self.reservation_ids.ids),
    #                         ('id', 'in', self.origin_reservation_ids.ids)]
    #     return action


    def add_supplier_category(self, res_partner_category):
        partner_category_id = self.env.ref(res_partner_category)
        if partner_category_id:
            if self.category_id and partner_category_id.id not in self.category_id.ids:
                old_list = self.category_id.ids
                new_value = [(6, 0, old_list.append(partner_category_id.id))]
            else:
                new_value = [(6, 0, [partner_category_id.id])]
            return new_value
        return False

