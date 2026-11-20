from app.models.auth import AuditLog, Role, RolePermission, Session, User  # noqa: F401
from app.models.core import (Customer, Vehicle, VehicleOwnership,  # noqa: F401
                             VehiclePlateHistory, VehicleVisit)
from app.models.jobs import (Inspection, InspectionItem, JobStatusHistory,  # noqa: F401
                             ReceptionRecord, RepairOperation, Technician, TechnicianAssignment)
from app.models.parts import (Approval, PartPurchase, PartReturn, Quotation,  # noqa: F401
                              QuotationItem, Supplier)
from app.models.billing import (CreditNote, Expense, ExpenseCategory, Invoice,  # noqa: F401
                                InvoiceItem, Payment, Refund)
from app.models.delivery import (Delivery, MaintenanceReminder, QualityCheck,  # noqa: F401
                                 Warranty, WarrantyClaim)
from app.models.system import AppSetting, BackupRecord  # noqa: F401
from app.models.files import Attachment  # noqa: F401
from app.models.inventory import (GoodsReceipt, GoodsReceiptLine, InventoryBalance, InventoryCategory,  # noqa: F401
                                  InventoryItem, PurchaseInvoice, PurchaseInvoiceLine, StockAdjustment,
                                  StockAdjustmentLine, StockMovement, StockReservation, SupplierCredit,
                                  SupplierPayment, Warehouse)
