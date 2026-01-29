from enum import Enum


class EventRegistrationStatus(Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID_CONFIRM_PENDING = "paid_confirm_pending"
    CONFIRMED = "confirmed"
    ATTENDED_CONFIRMED = "attended_confirmed"
    DECLINED = "declined"
