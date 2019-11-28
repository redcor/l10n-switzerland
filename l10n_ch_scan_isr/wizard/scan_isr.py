# -*- coding: utf-8 -*-
# Author: Nicolas Bessi Vincent Renaville
# Copyright 2013 Camptocamp SA
# Copyright 2015 Alex Comba - Agile Business Group
# Copyright 2016 Alvaro Estebanez - Brain-tec AG
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models, _
from odoo.exceptions import Warning as UserError


class ScanIsr(models.TransientModel):
    _name = "scan.isr"
    _description = "ISR/ESR Scanning Wizard"

    @api.model
    def _default_journal(self):
        if self.env.user.company_id:
            # We will get purchase journal linked with this company
            journals = self.env['account.journal'].search(
                [('type', '=', 'purchase'),
                 ('company_id', '=', self.env.user.company_id.id)],
            )
            if len(journals) == 1:
                return journals[0]
            else:
                return False
        else:
            return False

    journal_id = fields.Many2one(comodel_name='account.journal',
                                 string="Invoice journal",
                                 default=lambda self: self._default_journal())
    isr_string = fields.Char(size=128, string='ISR String')
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    bank_account_id = fields.Many2one(comodel_name='res.partner.bank',
                                      string="Partner Bank Account")
    state = fields.Selection(
        [('new', 'New'),
         ('valid', 'valid'),
         ('need_extra_info', 'Need extra information')],
        'State', default='new')

    def _check_number(self, part_validation):
        nTab = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
        resultnumber = 0
        for number in part_validation:
            resultnumber = nTab[(resultnumber + int(number) - 0) % 10]
        return (10 - resultnumber) % 10

    def _construct_isrplus_in_chf(self, isr_string):
        if len(isr_string) != 43:
            raise UserError(
                _('ISR CheckSum Error in first part')
            )
        elif self._check_number(isr_string[0:2]) != int(isr_string[2]):
            raise UserError(
                _('ISR CheckSum Error in second part')
            )
        elif self._check_number(isr_string[4:30]) != int(isr_string[30]):
            raise UserError(
                _('ISR CheckSum Error in third part')
            )
        elif self._check_number(isr_string[33:41]) != int(isr_string[41]):
            raise UserError(
                _('ISR CheckSum Error in fourth part')
            )
        else:
            isr_struct = {
                'type': isr_string[0:2],
                'amount': 0.0,
                'reference': isr_string[4:31],
                'isrnumber': isr_string[4:10],
                'beneficiaire': self._create_isr_account(isr_string[33:42]),
                'domain': '',
                'currency': ''
            }
            return isr_struct

    def _construct_isr_in_chf(self, isr_string):
        if len(isr_string) != 53:
            raise UserError(
                _('ISR CheckSum Error in first part')
            )
        elif self._check_number(isr_string[0:12]) != int(isr_string[12]):
            raise UserError(
                _('ISR CheckSum Error in second part')
            )
        elif self._check_number(isr_string[14:40]) != int(isr_string[40]):
            raise UserError(
                _('ISR CheckSum Error in third part')
            )
        elif self._check_number(isr_string[43:51]) != int(isr_string[51]):
            raise UserError(
                _('ISR CheckSum Error in fourth part')
            )
        else:
            isr_struct = {
                'type': isr_string[0:2],
                'amount': float(isr_string[2:12]) / 100,
                'reference': isr_string[14:41],
                'isrnumber': isr_string[14:20],
                'beneficiaire': self._create_isr_account(isr_string[43:52]),
                'domain': '',
                'currency': ''
            }
            return isr_struct

    def _construct_isr_postal_in_chf(self, isr_string):
        if len(isr_string) != 42:
            raise UserError(
                _('ISR CheckSum Error in first part')
            )
        else:
            isr_struct = {
                'type': isr_string[0:2],
                'amount': float(isr_string[2:12]) / 100,
                'reference': isr_string[14:30],
                'isrnumber': '000000',
                'beneficiaire': self._create_isr_account(isr_string[32:41]),
                'domain': '',
                'currency': ''
            }
            return isr_struct

    def _construct_isr_postal_other_in_chf(self, isr_string):
        if len(isr_string) != 41:
            raise UserError(
                _('ISR CheckSum Error in first part')
            )
        else:

            isr_struct = {
                'type': isr_string[0:2],
                'amount': float(isr_string[7:16]) / 100,
                'reference': isr_string[18:33],
                'isrnumber': '000000',
                'beneficiaire': self._create_isr_account(isr_string[34:40]),
                'domain': '',
                'currency': ''
            }
            return isr_struct

    def _create_invoice_line(self, data, invoice):
        move = self.env['account.move']
        invoice_line = invoice_line_model = self.env['account.move.line']
        # First we write partner_id
        self.write({'partner_id': data['partner_id']})
        # We check that this partner have a default product
        partner = self.env['res.partner'].browse(data['partner_id'])
        if data['bank_account']:
            account_info = self.env['res.partner.bank'].browse(
                data['bank_account'])
        prod = partner.supplier_invoice_default_product or \
               account_info.partner_id.supplier_invoice_default_product
        if prod:
            my_vals = {
                'product_id': prod.id,
                'move_id': data['move_id'],
            }
            specs = invoice_line_model._onchange_spec()
            default_values = invoice_line_model.default_get(specs)
            invoice_line_vals = {k: None for k in specs.keys()}
            invoice_line_vals.update(default_values)
            invoice_line_vals.update(my_vals)
            product_onchange_result = invoice_line_model.onchange(
                invoice_line_vals, ['product_id'], specs)
            value = product_onchange_result.get('value')

            for name, val in value.items():

                if isinstance(val, tuple):
                    value[name] = val[0]

            invoice_line_vals.update(value)

            invoice_line_vals.update(
                {'price_unit': data['isr_struct']['amount']})

            invoice_line = invoice.update(
                {'invoice_line_ids': [(0, 0, invoice_line_vals)]})
            invoice._recompute_payment_terms_lines()
            # We will check that the tax specified
            # on the product is price include or amount is 0
            try:
                if invoice_line.tax_ids:
                    for taxe in invoice_line.tax_ids:
                        if not taxe.price_include and taxe.amount != 0.0:
                            raise UserError(
                                _('The default product in this partner has '
                                  'wrong taxes configuration')
                            )
            except:
                pass
        return invoice_line

    def _create_direct_invoice(self, data):
        # We will call the function, that create invoice line
        invoice_model = self.env['account.move']
        currency_model = self.env['res.currency']
        today = fields.Date.today()
        if data['bank_account']:
            account_info = self.env['res.partner.bank'].browse(
                data['bank_account'])
        # We will now search the currency_id
        currency = currency_model.search(
            [('name', '=', data['isr_struct']['currency'])])
        if not currency:
            raise UserError(
                _('Unknown or deactivated currency: %s') % (
                    data['isr_struct']['currency'],
                )
            )
        invoice_date_due = today
        # We will now compute the due date and fixe the payment term
        invoice_payment_term_id = (account_info.partner_id.
                                   property_supplier_payment_term_id.id)
        if invoice_payment_term_id:
            # We Calculate @due_date
            # with self.env.do_in_onchange():
            virtual_inv = self.env['account.move'].new({
                'invoice_date': today,
                'invoice_payment_term_id': invoice_payment_term_id,
            })
            virtual_inv._onchange_invoice_date()
            invoice_date_due = virtual_inv.invoice_date_due

        invoice_vals = {
            'name': today,
            'partner_id': data['partner_id'] or account_info.partner_id.id,
            'invoice_date_due': invoice_date_due,
            'invoice_date': today,
            'invoice_payment_term_id': invoice_payment_term_id,
            # 'reference_type': 'isr',
            'ref': data['isr_struct']['reference'],
            'amount_total': data['isr_struct']['amount'],
            'invoice_partner_bank_id': account_info.id,
            'currency_id': currency.id,
            'journal_id': data['journal_id'],
            'type': 'in_invoice',
        }
        invoice = invoice_model.create(invoice_vals)
        data['move_id'] = invoice.id
        self._create_invoice_line(data, invoice)
        # Now we create taxes lines
        # invoice.compute_taxes()
        action = {
            'domain': "[('id','=', " + str(invoice.id) + ")]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': False,
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'res_id': invoice.id
        }
        return action

    def _create_isr_account(self, account_unformated):
        acc_len = len(account_unformated)
        account_formated = "%s-%s-%s" % (
            account_unformated[0:2],
            str(int(account_unformated[2:acc_len - 1])),
            account_unformated[acc_len - 1:acc_len]
        )
        return account_formated

    def _get_isr_structurated(self, isr_string):
        if isr_string is not False:
            # Get rid of leading and ending spaces of the ISR string
            isr_string = isr_string.strip()

            # We will get the 2 first digits of the ISR string in order
            # to know the ISR type of this account
            isr_type = isr_string[0:2]
            isr_struct = {}
            if isr_type == '01' and len(isr_string) == 42:
                # This ISR is the type of ISR in CHF
                # WE will call the function and Call
                isr_struct = self._construct_isr_postal_in_chf(isr_string)
                # We will set the currency , in this case it's allways CHF
                isr_struct['currency'] = 'CHF'
            elif isr_type == '01':
                # This ISR is the type of ISR in CHF
                # We will call the function and Call
                isr_struct = self._construct_isr_in_chf(isr_string)
                # We will set the currency , in this case it's allways CHF
                isr_struct['currency'] = 'CHF'
            elif isr_type == '03':
                # It will be (At this time) the same work
                # as for a standard ISR with 01 code
                isr_struct = self._construct_isr_postal_in_chf(isr_string)
                # We will set the currency , in this case it's allways CHF
                isr_struct['currency'] = 'CHF'
            elif isr_type == '04':
                # It the ISR postal in CHF
                isr_struct = self._construct_isrplus_in_chf(isr_string)
                # We will set the currency , in this case it's always CHF
                isr_struct['currency'] = 'CHF'
            elif isr_type == '21':
                # It for a ISR in Euro
                isr_struct = self._construct_isr_in_chf(isr_string)
                # We will set the currency , in this case it's allways CHF
                isr_struct['currency'] = 'EUR'
            ##
            elif isr_type == '31':
                # It the ISR postal in CHF
                isr_struct = self._construct_isrplus_in_chf(isr_string)
                # We will set the currency , in this case it's allways CHF
                isr_struct['currency'] = 'EUR'

            elif isr_type[0:1] == '<' and len(isr_string) == 41:
                # It the ISR postal in CHF
                isr_struct = self._construct_isr_postal_other_in_chf(
                    isr_string)
                # We will set the currency , in this case it's allways CHF
                isr_struct['currency'] = 'CHF'
            else:
                raise UserError(_('This kind of ISR is not supported '
                                  'at this time'))
            # We will test if the ISR has an Adherent Number if not we
            # will make the search of the account base on
            # his name non base on the ISR adherent number
            if (isr_struct['isrnumber'] == '000000'):
                isr_struct['domain'] = 'name'
            else:
                isr_struct['domain'] = 'l10n_ch_isrb_id_number'
            return isr_struct

    def validate_isr_string(self):
        self.ensure_one()
        # IsR Standrard
        # 0100003949753>120000000000234478943216899+ 010001628>
        # ISR without ISr Reference
        # 0100000229509>000000013052001000111870316+ 010618955>
        # ISR + In CHF
        # 042>904370000000000000007078109+ 010037882>
        # ISR In euro
        # 2100000440001>961116900000006600000009284+ 030001625>
        # <060001000313795> 110880150449186+ 43435>
        # <010001000165865> 951050156515104+ 43435>
        # <010001000060190> 052550152684006+ 43435>
        #
        # Explode and check  the ISR Number and structurate it
        #
        data = {}
        data['isr_struct'] = self._get_isr_structurated(self.isr_string)
        partner_bank_model = self.env['res.partner.bank']
        partner_bank = False
        # We will now search the account linked with this ISR
        if data['isr_struct']['domain'] == 'name':
            domain = [
                ('l10n_ch_postal', '=', data['isr_struct']['beneficiaire'])]
        else:
            domain = [
                ('l10n_ch_postal', '=', data['isr_struct']['beneficiaire']), (
                    'l10n_ch_isrb_id_number', '=',
                    data['isr_struct']['isrnumber'])]
        partner_bank = partner_bank_model.search(domain, limit=1)
        # We will need to know if we need to create invoice line
        if partner_bank:
            # We have found the account corresponding to the
            # isr_adhreent_number
            # so we can directly create the account
            data['id'] = self.id
            data['partner_id'] = partner_bank.partner_id.id
            data['bank_account'] = partner_bank.id
            data['journal_id'] = self.journal_id.id
            action = self._create_direct_invoice(data)
            return action
        elif self.bank_account_id:
            data['id'] = self.id
            data['partner_id'] = self.partner_id.id
            data['journal_id'] = self.journal_id.id
            data['bank_account'] = self.bank_account_id.id
            # We will write the adherent IsR number if we have one
            # for the future invoice
            if data['isr_struct']['domain'] == 'l10n_ch_isrb_id_number':
                self.bank_account_id.l10n_ch_isrb_id_number = \
                    data['isr_struct']['isrnumber']
            action = self._create_direct_invoice(data)
            return action
        else:
            # we haven't found a valid l10n_ch_isrb_id_numberber
            # we will need to create or update a bank account
            self.state = 'need_extra_info'
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'scan.isr',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new',
            }
