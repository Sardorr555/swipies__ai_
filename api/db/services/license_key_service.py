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
