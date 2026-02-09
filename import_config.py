import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from china_bean_importers import wechat, alipay_web, alipay_mobile, boc_credit_card, boc_debit_card, cmb_debit_card

from config import config # your config file name

CONFIG = [
    wechat.Importer(config),
    alipay_web.Importer(config),
    alipay_mobile.Importer(config),
    boc_credit_card.Importer(config),
    boc_debit_card.Importer(config),
    cmb_debit_card.Importer(config),
]
