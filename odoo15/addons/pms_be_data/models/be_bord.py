from odoo import api, fields, models


class BeBoard(models.Model):
    _name = "be.board"
    _description = "Board"
    _rec_name = 'code'


    name = fields.Char('Board Name', required=True)
    code = fields.Char(string='code', required=True, size=2)
    price = fields.Integer('price',required=True)
