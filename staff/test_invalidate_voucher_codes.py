from datetime import datetime, timezone, timedelta

from app_ccf.models import VoucherCode, VoucherCodeBatch

from .utils import (invalidate_voucher_codes_with_campaign,
                    invalidate_voucher_codes_with_code_list)
from app_ccf import base_test


class InvalidateVoucherCodesTests(base_test.CcfBaseTest):

    def test_invalidate_voucher_codes_with_campaign(self):
        COMBOS = [
            ('aff_x', 'cam_a'),
            ('aff_x', 'cam_b'),
            ('aff_y', 'cam_a'),
            ('aff_y', 'cam_b'),
        ]

        fields = {
            'base_amount': 400,
            'num_codes': 1,
            'code_length': 2,
            'created': datetime.now(timezone.utc),
            'expiration_date': datetime.now(timezone.utc) + timedelta(days=1),
            'channel': 'test_channel'
        }
        voucher_codes = []
        for affiliate, campaign in COMBOS:
            voucher_code = VoucherCode.objects.create(
                added_amount=0,
                code=affiliate[-1] + campaign[-1],
                batch=VoucherCodeBatch.objects.create(
                    **fields,
                    affiliate=affiliate,
                    campaign=campaign,
                )
            )
            voucher_code.full_clean()
            voucher_codes.append(voucher_code)

        target_affiliate, target_campaign = COMBOS[2]
        invalidate_voucher_codes_with_campaign(affiliate=target_affiliate,
                                               campaign=target_campaign)

        for voucher_code in voucher_codes:
            voucher_code.refresh_from_db()
            if (voucher_code.affiliate == target_affiliate
                    and voucher_code.campaign == target_campaign):
                self.assertFalse(voucher_code.is_active)
            else:
                self.assertTrue(voucher_code.is_active)

    def test_invalidate_voucher_codes_with_code_list(self):
        CODE_A = 'a'
        CODE_B = 'b'
        CODE_C = 'c'

        fields = {
            'added_amount': 0,
            'batch':  VoucherCodeBatch.objects.create(
                num_codes=1,
                code_length=9,
                base_amount=400,
                created=datetime.now(),
                expiration_date=datetime.now())
        }
        VoucherCode.objects.create(
            **fields,
            code=CODE_A)
        VoucherCode.objects.create(
            **fields,
            code=CODE_B)
        VoucherCode.objects.create(
            **fields,
            code=CODE_C)
        for voucher_code in VoucherCode.objects.filter():
            voucher_code.full_clean()

        invalidate_voucher_codes_with_code_list([CODE_A, CODE_B])

        self.assertFalse(VoucherCode.objects.get(code=CODE_A).is_active)
        self.assertFalse(VoucherCode.objects.get(code=CODE_B).is_active)
        self.assertTrue(VoucherCode.objects.get(code=CODE_C).is_active)
