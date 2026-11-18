"""Customer consent for linked work in sent quotes; drafts never authorize work."""
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.models import Quotation, QuotationItem, VehicleVisit


def lock_job(db: Session, job_id) -> None:
    # Serialize sent/approved quote decisions with execution on the same job.
    db.execute(select(VehicleVisit.id).where(VehicleVisit.id == job_id).with_for_update())


def require_work_approval(db: Session, job_id, *, operation_id=None, part_id=None,
                          amount: Decimal) -> None:
    lock_job(db, job_id)
    relation = (QuotationItem.part_id == part_id) if part_id is not None else (
        (QuotationItem.operation_id == operation_id) & (QuotationItem.kind == "labor"))
    item = db.scalar(select(QuotationItem).join(Quotation, Quotation.id == QuotationItem.quotation_id)
                     .where(Quotation.visit_id == job_id, Quotation.sent_at.is_not(None), relation)
                     .order_by(Quotation.sent_at.desc(), Quotation.quote_no.desc(), QuotationItem.id.desc()).limit(1))
    if item is None:
        if db.scalar(select(Quotation.id).where(Quotation.visit_id == job_id,
                                                Quotation.sent_at.is_not(None)).limit(1)):
            raise AppError("البند غير مدرج في عرض سعر مرسل؛ أضفه لعرض جديد وسجّل موافقة العميل", 409,
                           "work_not_quoted")
        return  # Jobs without sent quotations retain the quick-service path.
    if item.approval_state != "approved":
        raise AppError("راجع عرض السعر وسجّل موافقة العميل على هذا البند قبل التنفيذ", 409,
                       "customer_approval_required")
    if amount > Decimal(item.amount):
        raise AppError("قيمة البند زادت عن المبلغ المعتمد؛ أرسل عرض سعر جديداً وسجّل موافقة العميل", 409,
                       "quotation_amount_exceeded")
