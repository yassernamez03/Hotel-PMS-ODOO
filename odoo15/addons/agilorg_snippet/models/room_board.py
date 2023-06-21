from odoo import api, fields, models


class BeBoard(models.Model):
    _name = "hotel.room_board"
    _description = "Board"
    _rec_name = 'code'

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char('Board Name', required=True)
    code = fields.Char(string='code', required=True, size=2)
    price = fields.Integer('price',required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=_get_default_currency_id, required=True)

