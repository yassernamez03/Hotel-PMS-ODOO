from odoo import api, fields, models, _

TAX_RULE = [('pax_night','Per Night and Pax'),
            ('night','Per Night'),
            ('per_pax', 'Per Pax'),
            ('stay', 'Percentage of the stay amount')
            ]

TAX_TYPES = [('amount','Amount'),
             ('percent', 'Percent'),
            ]

TAX_DESCRIPTION = [('city', 'City'),
                  ('local', 'Local'),
                  ('resort', 'Resort Fee'),
                  ('spot', 'Supplement to be paid on Spot'),
                 ]


class OtaTaxes(models.Model):
    _name = "be.taxes"
    _description = "OTA Taxes"

    @api.depends('description','type','value','currency_id')
    def compute_tax(self):
        for rec in self:
            rec.name = 'Taxe %s - %s - %s - %s' % (rec.description,rec.type, rec.value,rec.currency_id.name)
            if rec.type == 'amount':
                rec.amount = rec.value
                rec.percent = False
            elif rec.type == 'percent':
                rec.percent = rec.value
                rec.amount = False

    name = fields.Char('Taxe Name', compute='compute_tax')
    code = fields.Char('Taxe Code', required=False)
    product_id = fields.Many2one('product.product', string="Product Taxe")
    tax_rule = fields.Selection(TAX_RULE,
                                string='Tax Rule',
                                default='pax_night',
                                required=True)
    value = fields.Float(string='Amount or Percent', digits='Taxe Value')
    type = fields.Selection(TAX_TYPES,
                            string='Type',
                            default='amount',
                            required=True)

    description = fields.Selection(TAX_DESCRIPTION,
                                   string='Description',
                                   default='city',
                                   required=True)
    included_tax = fields.Boolean(string='Included in Price', default=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    amount = fields.Float(string='Tax Amount', compute='compute_tax', store=True)
    percent = fields.Float(string='Tax Percent', compute='compute_tax', store=True)



    def get_city_tax_value(self, taxes,nights=1, pax=1, total_stay=0):
        # Returns the amount of taxes applied
        tax_product = self.env.user.company_id.city_tax_product_id
        applied_taxes = self.compute_taxes(taxes,nights=nights, pax=pax, total_stay=total_stay)
        total_city_tax = included = excluded = 0.
        tax_ids = []
        for tax in applied_taxes:
            total_city_tax = + tax['amount']
            tax_ids = tax_ids.append(tax['tax_id'].id)
            included = + tax['included']
            excluded = + tax['excluded']

        return {
            'tax_product': tax_product,
            'amount': total_city_tax,
            'included': included,
            'excluded': excluded,
            'tax_ids': [(6, 0, tax_ids)]
        }

    def compute_taxes(self,taxes,nights=1, pax=1, total_stay=0):
        applied_taxes = []
        for tax in taxes:
            if tax.amount:
                if tax.tax_rule == 'pax_night':
                    tax_base = nights * pax
                elif tax.tax_rule == 'night':
                    tax_base = nights
                else:
                    tax_base = pax
                city_tax = tax_base * tax.amount
            else:
                tax_base = total_stay
                city_tax = (total_stay * tax.percent) / 100

            if city_tax:
                applied_taxes.append({
                    'tax_id': tax,
                    'tax_base': tax_base,
                    'amount': city_tax,
                    'included': city_tax if tax.included_tax else 0.,
                    'excluded': city_tax if not tax.included_tax else 0.,
                })
        return applied_taxes
