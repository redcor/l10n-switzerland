# Copyright 2012-2019 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import common
from odoo import exceptions
from odoo.tests.common import Form


class TestCreateMove(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref('base.main_company')
        cls.partner = cls.env.ref('base.res_partner_12')
        bank = cls.env['res.bank'].create({
            'name': 'BCV',
            'bic': 'BBRUBEBB',
            'clearing': '234234',
        })
        # define company bank account
        cls.bank_journal = cls.env['account.journal'].create({
            'company_id': cls.company.id,
            'type': 'bank',
            'code': 'BNK42',
            'bank_id': bank.id,
            'bank_acc_number': '01-1234-1',
        })
        cls.bank_acc = cls.bank_journal.bank_account_id
        cls.bank_acc.write({
            'l10n_ch_isr_subscription_chf': '01-162-8',
            'sequence': 1,
        })
        fields_list = [
            'company_id',
            'user_id',
            'currency_id',
            'journal_id',
        ]
        cls.inv_values = cls.env['account.move'].default_get(fields_list)

    def new_form(self):
        inv = Form(self.env['account.move'].with_context(default_type='out_invoice'))
        # Form(
        #     self.env['account.move'],
        #     view='account.view_move_form'
        # )
        inv.partner_id = self.partner
        inv.journal_id = self.bank_journal
        return inv

    def test_emit_move_with_isr_reference(self):
        inv_form = self.new_form()
        move = inv_form.save()
        self.assertFalse(move._is_isr_reference())

        inv_form.reference = '132000000000000000000000014'
        inv_form.save()
        self.assertTrue(move._is_isr_reference())

    def test_emit_move_with_isr_reference_15_pos(self):
        inv_form = self.new_form()
        move = inv_form.save()

        self.assertFalse(move._is_isr_reference())

        move.reference = '132000000000004'
        # We consider such reference to be unstructured
        # and we shouldn't generate such references
        self.assertFalse(move._is_isr_reference())

        # and save
        inv_form.save()

    def test_emit_move_with_non_isr_reference(self):
        inv_form = self.new_form()
        move = inv_form.save()

        self.assertFalse(move._is_isr_reference())

        move.reference = 'Not a ISR ref with 27 chars'
        self.assertFalse(move._is_isr_reference())

    def test_emit_move_with_missing_isr_reference(self):
        inv_form = self.new_form()
        # set dummy account to be replaced by onchange
        inv_form.account_id = self.env['account.account'].browse(1)
        inv_form.save()

        inv_form.reference = False
        # and save
        move = inv_form.save()

        self.assertFalse(move._is_isr_reference())

    def test_emit_move_with_isr_reference_missing_subscr_num(self):
        inv_form = self.new_form()
        move = inv_form.save()
        inv_form.save()
        self.assertFalse(move._is_isr_reference())
        inv_form.partner_bank_id = False
        with self.assertRaises(exceptions.ValidationError):
            inv_form.reference = '132000000000000000000000014'
            inv_form.save()

    def test_emit_move_with_isr_reference_missing_subscr_num(self):
        inv_form = self.new_form()
        move = inv_form.save()
        inv_form.save()
        self.assertFalse(move._is_isr_reference())
        self.bank_acc.l10n_ch_isr_subscription_chf = False
        with self.assertRaises(exceptions.ValidationError):
            inv_form.reference = '132000000000000000000000014'
            inv_form.save()

    def test_emit_move_with_isr_reference_subscr_num_wrong_currency(self):
        inv_form = self.new_form()
        move = inv_form.save()
        inv_form.save()
        self.assertFalse(move._is_isr_reference())
        move.currency_id = self.env.ref('base.EUR')
        with self.assertRaises(exceptions.ValidationError):
            inv_form.reference = '132000000000000000000000014'
            inv_form.save()
