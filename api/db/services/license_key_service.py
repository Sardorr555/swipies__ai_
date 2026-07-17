from api.db.db_models import DB, LicenseKey
from api.db.services.common_service import CommonService

class LicenseKeyService(CommonService):
    model = LicenseKey

    @classmethod
    @DB.connection_context()
    def get_by_user(cls, user_id: str):
        return list(cls.model.select().where(cls.model.user_id == user_id).order_by(cls.model.create_time.desc()).dicts())

    @classmethod
    @DB.connection_context()
    def get_all_licenses(cls, page_number=1, items_per_page=10, keywords=None):
        query = cls.model.select()
        if keywords:
            from peewee import fn
            query = query.where(
                fn.LOWER(cls.model.name).contains(keywords.lower()) |
                fn.LOWER(cls.model.license_key).contains(keywords.lower()) |
                fn.LOWER(cls.model.user_id).contains(keywords.lower()) |
                fn.LOWER(cls.model.status).contains(keywords.lower())
            )
        query = query.order_by(cls.model.create_time.desc())
        total = query.count()
        if page_number and items_per_page:
            query = query.paginate(page_number, items_per_page)
        return list(query.dicts()), total

    @classmethod
    @DB.connection_context()
    def get_license_pricing(cls):
        from api.db.services.system_settings_service import SystemSettingsService
        import json
        try:
            records = SystemSettingsService.get_by_name("license_price")
            if records:
                return json.loads(records[0].value)
        except Exception:
            pass
        return {
            "price_6_months": 300000.0,
            "price_12_months": 500000.0,
            "price_per_month_custom": 50000.0
        }

    @classmethod
    @DB.connection_context()
    def set_license_pricing(cls, pricing_dict):
        from api.db.services.system_settings_service import SystemSettingsService
        from common.time_utils import current_timestamp, datetime_format
        from datetime import datetime
        import json
        value_str = json.dumps(pricing_dict)
        records = SystemSettingsService.get_by_name("license_price")
        if records:
            SystemSettingsService.update_by_name("license_price", {
                "name": "license_price",
                "source": "database",
                "data_type": "json",
                "value": value_str
            })
        else:
            timestamp = current_timestamp()
            cur_datetime = datetime_format(datetime.now())
            SystemSettingsService.model.create(**{
                "name": "license_price",
                "source": "database",
                "data_type": "json",
                "value": value_str,
                "create_time": timestamp,
                "create_date": cur_datetime,
                "update_time": timestamp,
                "update_date": cur_datetime
            })
        return pricing_dict
