from china_bean_importers.common import BillDetailMapping as BDM

config = {
    "importers": {
        "alipay": {
            "account": "Assets:Alipay",
            "huabei_account": "Liabilities:Alipay:HuaBei",
            "douyin_monthly_payment_account": "Liabilities:DouyinMonthlyPayment",
            "yuebao_account": "Assets:Alipay:YuEBao",
            "red_packet_income_account": "Income:Alipay:RedPacket",
            "red_packet_expense_account": "Expenses:Alipay:RedPacket",
            "category_mapping": {
                "交通出行": "Expenses:Travel",
            },
        },
        "wechat": {
            "account": "Assets:WeChat:Wallet",
            "lingqiantong_account": "Assets:WeChat:LingQianTong",
            "red_packet_income_account": "Income:WeChat:RedPacket",
            "red_packet_expense_account": "Expenses:WeChat:RedPacket",
            "family_card_expense_account": "Expenses:WeChat:FamilyCard",
            "group_payment_expense_account": "Expenses:WeChat:Group",
            "group_payment_income_account": "Income:WeChat:Group",
            "transfer_expense_account": "Expenses:WeChat:Transfer",
            "transfer_income_account": "Income:WeChat:Transfer",
            "category_mapping": {
                "商户消费": "Expenses:Shopping:Unclassified",
                "扫二维码付款": "Expenses:QRCode",
                "信用卡还款": "Liabilities:CreditCard",
            },
            "detail_mappings": [
                # 中信银行还款
                BDM([], ["中信银行信用卡还款"], "Liabilities:CreditCard:CITIC:7310", [], {}),
                BDM([], ["天猫养车"], "Expenses:Vehicle:Unclassified", [], {}),
                BDM(["浙里惠民保","保险费","保费","保险人"], [], "Expenses:Insurance", [], {}),
                BDM(["充值"], [], "Expenses:UtilityPayment", [], {}),
                BDM([], ["携程"], "Expenses:Travel", [], {}),
                BDM(["酒店"], [], "Expenses:Travel", [], {}),
            ]
        },
        "ccb_debit_card":{
            "account": "Assets:Bank:CCB:4582",
            "detail_mappings": [
                # 公积金补充匹配，默认为公积金中心转账
                # 公积金贴息为income，需手动修改
                BDM(["公积金"], ["公积金管理中心"], "Assets:Government:HousingFund", [], {}),
            ]
        },
        "thu_ecard": {
            "account": "Assets:Card:THU",
        },
        "hsbc_hk": {
            "account_mapping": {
                "One": "Assets:Bank:HSBC",
                "PULSE": "Liabilities:CreditCards:HSBC:Pulse",
            },
            "use_cnh": False,
        },
        "boc": {
            "credit": {
                "extract_repayment_rate": False, # Boolean, or predicate function (account, narration) -> bool
                "repayment_tag": None, # String, or function (account, narration) -> str
            },
        },
        "card_narration_whitelist": ["财付通(银联云闪付)"],
        "card_narration_blacklist": ["支付宝", "财付通", "美团支付"],
    },
    "card_accounts": {
        "Liabilities:Card": {
            "BoC": ["1234", "5678"],
            "CMB": ["1111", "2222"],
        },
        "Assets:Card": {
            "BoC": ["4321", "8765"],
            "CMB": ["6214831013762379", "6214831013762379"],
        },
    },
    "pdf_passwords": [""],
    # account matching
    "unknown_expense_account": "Expenses:Unknown",
    "unknown_income_account": "Income:Unknown",
    # common mapping
    # narration,payees,destination,tags,metadata
    # narration 和 payee 都设置，则匹配同时满足关系的bill
    "detail_mappings": [
        # QIQI零钱存入
        BDM(["qiqimick"], ["小宝零花钱"], "Assets:Alipay:LingQian", [], {}),
        # 余额宝收益收入
        BDM(["收益发放"], [], "Income:Investing", [], {}),
        BDM(["京东"], [], "Expenses:JD", [], {"platform": "京东"}),
        BDM([], ["饿了么"], "Expenses:Food:Delivery", [], {"platform": "饿了么"}),
        BDM([], ["万龙运动旅游"], None, ["ski"], {}),
    ],
}
