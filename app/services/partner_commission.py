from config.config import settings

DEFAULT_PARTNER_COMMISSION_PERCENT = 20


def get_default_partner_commission_percent() -> int:
    partner_settings = settings.get("partner", {}) or {}
    raw_value = (
        partner_settings.get("default_commission_percent")
        if isinstance(partner_settings, dict)
        else getattr(partner_settings, "default_commission_percent", None)
    )
    if raw_value is None:
        raw_value = DEFAULT_PARTNER_COMMISSION_PERCENT
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = DEFAULT_PARTNER_COMMISSION_PERCENT
    return min(100, max(0, value))
