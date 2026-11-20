"""Workshop inventory & purchasing module (additive: no existing table is dropped or rewritten).

* new tables: categories, warehouses, items, balances, the append-only stock-movement ledger, reservations, purchase invoices and
  lines, goods receipts and lines, supplier payments and credits, stock adjustments and lines;
* part_purchases gets source / inventory_item_id / warehouse_id / issued_qty (existing rows become source='direct', i.e. unchanged);
  unit_cost is widened from 2 to 4 decimals so a weighted-average issue cost is kept exactly (existing values are preserved);
* part_returns gets disposition (existing rows become 'supplier', i.e. unchanged);
* database guards: the ledger is append-only, posted purchase invoices are immutable, supplier payments are never deleted;
* a default warehouse "Main Workshop Warehouse / المخزن الرئيسي للورشة" is created.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

QTY = sa.Numeric(14, 3)
COST = sa.Numeric(14, 4)
MONEY = sa.Numeric(14, 2)
VALUE = sa.Numeric(16, 4)
NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "inventory_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name_en", sa.String(120), nullable=False),
        sa.Column("name_ar", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["inventory_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_categories_parent_id", "inventory_categories", ["parent_id"])
    op.execute("CREATE UNIQUE INDEX uq_inventory_categories_name ON inventory_categories (coalesce(parent_id, 0), lower(name_en))")

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name_en", sa.String(120), nullable=False),
        sa.Column("name_ar", sa.String(120), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.execute("CREATE UNIQUE INDEX uq_warehouses_one_default ON warehouses (is_default) WHERE is_default")
    op.execute("INSERT INTO warehouses (code, name_en, name_ar, is_default, is_active) "
               "VALUES ('MAIN', 'Main Workshop Warehouse', 'المخزن الرئيسي للورشة', true, true)")

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku", sa.String(60), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("mfr_part_no", sa.String(100), nullable=True),
        sa.Column("oem_part_no", sa.String(100), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("uom", sa.String(20), server_default="pcs", nullable=False),
        sa.Column("default_supplier_id", sa.Integer(), nullable=True),
        sa.Column("purchase_price", COST, server_default="0", nullable=False),
        sa.Column("selling_price", MONEY, server_default="0", nullable=False),
        sa.Column("min_stock", QTY, server_default="0", nullable=False),
        sa.Column("reorder_qty", QTY, server_default="0", nullable=False),
        sa.Column("storage_location", sa.String(100), nullable=True),
        sa.Column("compatibility", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["inventory_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["inventory_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["default_supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
        sa.CheckConstraint("purchase_price >= 0 AND selling_price >= 0 AND min_stock >= 0 AND reorder_qty >= 0", name="ck_inventory_items_nonneg"),
    )
    op.create_index("ix_inventory_items_category_id", "inventory_items", ["category_id"])
    op.create_index("ix_inventory_items_oem_part_no", "inventory_items", ["oem_part_no"])
    op.create_index("ix_inventory_items_name_en", "inventory_items", [sa.text("lower(name_en)")])
    op.execute("CREATE UNIQUE INDEX uq_inventory_items_barcode ON inventory_items (barcode) WHERE barcode IS NOT NULL")
    # the same manufacturer part of the same brand is one master record (several suppliers / prices are separate data)
    op.execute("CREATE UNIQUE INDEX uq_inventory_items_mfr ON inventory_items (coalesce(lower(brand), ''), lower(mfr_part_no)) WHERE mfr_part_no IS NOT NULL")

    op.create_table(
        "inventory_balances",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("on_hand", QTY, server_default="0", nullable=False),
        sa.Column("reserved", QTY, server_default="0", nullable=False),
        sa.Column("value", VALUE, server_default="0", nullable=False),
        sa.Column("last_cost", COST, server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("item_id", "warehouse_id"),
        # the database itself refuses to oversell, whatever the application does
        sa.CheckConstraint("on_hand >= 0 AND reserved >= 0 AND reserved <= on_hand AND value >= 0", name="ck_inventory_balances_sane"),
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(24), nullable=False),
        sa.Column("qty", QTY, nullable=False),
        sa.Column("reserved_delta", QTY, server_default="0", nullable=False),
        sa.Column("unit_cost", COST, server_default="0", nullable=False),
        sa.Column("value_delta", VALUE, server_default="0", nullable=False),
        sa.Column("on_hand_after", QTY, nullable=False),
        sa.Column("value_after", VALUE, nullable=False),
        sa.Column("doc_type", sa.String(30), nullable=True),
        sa.Column("doc_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.Integer(), nullable=True),
        sa.Column("visit_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("reverses_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["part_id"], ["part_purchases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["visit_id"], ["vehicle_visits.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reverses_id"], ["stock_movements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("reverses_id"),  # a movement can be reversed only once
        sa.CheckConstraint("movement_type IN ('OPENING','GOODS_RECEIPT','RESERVE','RELEASE','ISSUE','RETURN_TO_WAREHOUSE','SUPPLIER_RETURN',"
                           "'ADJUSTMENT','COUNT','TRANSFER_OUT','TRANSFER_IN','REVERSAL')", name="ck_stock_movements_type"),
    )
    op.create_index("ix_stock_movements_ts", "stock_movements", ["ts"])
    op.create_index("ix_stock_movements_item_ts", "stock_movements", ["item_id", "ts"])
    op.create_index("ix_stock_movements_doc", "stock_movements", ["doc_type", "doc_id"])
    op.create_index("ix_stock_movements_part_id", "stock_movements", ["part_id"])
    op.create_index("ix_stock_movements_visit_id", "stock_movements", ["visit_id"])
    op.execute("CREATE UNIQUE INDEX uq_stock_movements_opening ON stock_movements (item_id, warehouse_id) WHERE movement_type = 'OPENING'")

    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("part_id", sa.Integer(), nullable=False),
        sa.Column("qty", QTY, nullable=False),
        sa.Column("status", sa.String(12), server_default="active", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["part_id"], ["part_purchases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("qty > 0 AND status IN ('active','consumed','released')", name="ck_stock_reservations"),
    )
    op.create_index("ix_stock_reservations_item_id", "stock_reservations", ["item_id"])
    op.create_index("ix_stock_reservations_part_id", "stock_reservations", ["part_id"])
    op.execute("CREATE UNIQUE INDEX uq_stock_reservations_active ON stock_reservations (part_id) WHERE status = 'active'")

    op.create_table(
        "purchase_invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("supplier_invoice_no", sa.String(100), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), server_default="draft", nullable=False),
        sa.Column("receipt_status", sa.String(12), server_default="none", nullable=False),
        sa.Column("subtotal", MONEY, server_default="0", nullable=False),
        sa.Column("discount", MONEY, server_default="0", nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("tax_amount", MONEY, server_default="0", nullable=False),
        sa.Column("total", MONEY, server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint("status IN ('draft','posted','cancelled') AND receipt_status IN ('none','partial','full')", name="ck_purchase_invoices_state"),
    )
    op.create_index("ix_purchase_invoices_supplier_id", "purchase_invoices", ["supplier_id"])
    # the same supplier invoice number cannot be entered twice (a cancelled one may be entered again)
    op.execute("CREATE UNIQUE INDEX uq_purchase_invoices_supplier_no ON purchase_invoices (supplier_id, lower(supplier_invoice_no)) WHERE status <> 'cancelled'")

    op.create_table(
        "purchase_invoice_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("qty_ordered", QTY, nullable=False),
        sa.Column("qty_received", QTY, server_default="0", nullable=False),
        sa.Column("received_value", VALUE, server_default="0", nullable=False),
        sa.Column("unit_cost", COST, nullable=False),
        sa.Column("discount", MONEY, server_default="0", nullable=False),
        sa.Column("line_total", MONEY, nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("qty_ordered > 0 AND qty_received >= 0 AND qty_received <= qty_ordered AND unit_cost >= 0 AND discount >= 0",
                           name="ck_purchase_invoice_lines"),
    )
    op.create_index("ix_purchase_invoice_lines_invoice_id", "purchase_invoice_lines", ["invoice_id"])
    op.create_index("ix_purchase_invoice_lines_item_id", "purchase_invoice_lines", ["item_id"])

    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), server_default="posted", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("received_by", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverse_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint("status IN ('posted','reversed')", name="ck_goods_receipts_status"),
    )
    op.create_index("ix_goods_receipts_invoice_id", "goods_receipts", ["invoice_id"])

    op.create_table(
        "goods_receipt_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("invoice_line_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("qty", QTY, nullable=False),
        sa.Column("unit_cost", COST, nullable=False),
        sa.Column("value", VALUE, nullable=False),
        sa.Column("movement_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["receipt_id"], ["goods_receipts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_line_id"], ["purchase_invoice_lines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["movement_id"], ["stock_movements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("qty > 0", name="ck_goods_receipt_lines_qty"),
    )
    op.create_index("ix_goods_receipt_lines_receipt_id", "goods_receipt_lines", ["receipt_id"])

    op.create_table(
        "supplier_payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("paid_by", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["paid_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_supplier_payments_amount"),
    )
    op.create_index("ix_supplier_payments_invoice_id", "supplier_payments", ["invoice_id"])
    op.create_index("ix_supplier_payments_supplier_id", "supplier_payments", ["supplier_id"])

    op.create_table(
        "supplier_credits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("movement_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["movement_id"], ["stock_movements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_supplier_credits_amount"),
    )
    op.create_index("ix_supplier_credits_supplier_id", "supplier_credits", ["supplier_id"])
    op.create_index("ix_supplier_credits_invoice_id", "supplier_credits", ["invoice_id"])

    op.create_table(
        "stock_adjustments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), sa.Identity(always=False, start=1), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint("kind IN ('adjustment','count')", name="ck_stock_adjustments_kind"),
    )
    op.create_table(
        "stock_adjustment_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("adjustment_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("system_qty", QTY, nullable=False),
        sa.Column("counted_qty", QTY, nullable=True),
        sa.Column("qty_delta", QTY, nullable=False),
        sa.Column("unit_cost", COST, nullable=False),
        sa.Column("movement_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["adjustment_id"], ["stock_adjustments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["movement_id"], ["stock_movements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_adjustment_lines_adjustment_id", "stock_adjustment_lines", ["adjustment_id"])

    # ---- existing tables: additive columns only ----------------------------------------------------------------------
    op.add_column("part_purchases", sa.Column("source", sa.String(12), server_default="direct", nullable=False))
    op.add_column("part_purchases", sa.Column("inventory_item_id", sa.Integer(), nullable=True))
    op.add_column("part_purchases", sa.Column("warehouse_id", sa.Integer(), nullable=True))
    op.add_column("part_purchases", sa.Column("issued_qty", QTY, server_default="0", nullable=False))
    op.create_foreign_key("fk_part_purchases_inventory_item", "part_purchases", "inventory_items", ["inventory_item_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_part_purchases_warehouse", "part_purchases", "warehouses", ["warehouse_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_part_purchases_inventory_item_id", "part_purchases", ["inventory_item_id"])
    op.create_check_constraint("ck_part_purchases_source", "part_purchases", "source IN ('direct','warehouse','customer')")
    op.create_check_constraint("ck_part_purchases_warehouse_item", "part_purchases", "(source = 'warehouse') = (inventory_item_id IS NOT NULL)")
    op.alter_column("part_purchases", "unit_cost", type_=COST, existing_type=MONEY, existing_nullable=False)  # widening: values preserved
    op.add_column("part_returns", sa.Column("disposition", sa.String(12), server_default="supplier", nullable=False))
    op.create_check_constraint("ck_part_returns_disposition", "part_returns", "disposition IN ('supplier','warehouse','defective','used')")

    # ---- database guards ----------------------------------------------------------------------------------------------
    op.execute("""
        CREATE FUNCTION stock_movements_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'stock_movements is append-only; post a reversal movement instead';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER stock_movements_no_change BEFORE UPDATE OR DELETE ON stock_movements "
               "FOR EACH ROW EXECUTE FUNCTION stock_movements_immutable()")
    op.execute("""
        CREATE FUNCTION supplier_money_no_change() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'supplier payments and credits are never edited or deleted';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER supplier_payments_no_change BEFORE UPDATE OR DELETE ON supplier_payments "
               "FOR EACH ROW EXECUTE FUNCTION supplier_money_no_change()")
    op.execute("CREATE TRIGGER supplier_credits_no_change BEFORE UPDATE OR DELETE ON supplier_credits "
               "FOR EACH ROW EXECUTE FUNCTION supplier_money_no_change()")
    op.execute("""
        CREATE FUNCTION purchase_invoices_guard() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.status <> 'draft' THEN RAISE EXCEPTION 'posted purchase invoices cannot be deleted'; END IF;
                RETURN OLD;
            END IF;
            IF OLD.status <> 'draft' AND (
                NEW.number, NEW.supplier_id, NEW.supplier_invoice_no, NEW.invoice_date, NEW.warehouse_id,
                NEW.subtotal, NEW.discount, NEW.tax_rate, NEW.tax_amount, NEW.total
            ) IS DISTINCT FROM (
                OLD.number, OLD.supplier_id, OLD.supplier_invoice_no, OLD.invoice_date, OLD.warehouse_id,
                OLD.subtotal, OLD.discount, OLD.tax_rate, OLD.tax_amount, OLD.total
            ) THEN
                RAISE EXCEPTION 'posted purchase invoices are immutable';
            END IF;
            IF OLD.status = 'cancelled' AND NEW.status <> 'cancelled' THEN
                RAISE EXCEPTION 'cancelled purchase invoices cannot be reopened';
            END IF;
            IF OLD.status = 'posted' AND NEW.status = 'draft' THEN
                RAISE EXCEPTION 'a posted purchase invoice cannot go back to draft';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER purchase_invoices_guard_trg BEFORE UPDATE OR DELETE ON purchase_invoices "
               "FOR EACH ROW EXECUTE FUNCTION purchase_invoices_guard()")
    op.execute("""
        CREATE FUNCTION purchase_invoice_lines_guard() RETURNS trigger AS $$
        DECLARE inv_status text; inv_id uuid;
        BEGIN
            inv_id := CASE WHEN TG_OP = 'INSERT' THEN NEW.invoice_id ELSE OLD.invoice_id END;
            SELECT status INTO inv_status FROM purchase_invoices WHERE id = inv_id;
            IF inv_status = 'draft' THEN
                RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END IF;
            -- on a posted invoice only the received quantity / value may move
            IF TG_OP = 'UPDATE' AND (NEW.invoice_id, NEW.item_id, NEW.qty_ordered, NEW.unit_cost, NEW.discount, NEW.line_total)
               IS NOT DISTINCT FROM (OLD.invoice_id, OLD.item_id, OLD.qty_ordered, OLD.unit_cost, OLD.discount, OLD.line_total) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'lines of a posted purchase invoice are immutable';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("CREATE TRIGGER purchase_invoice_lines_guard_trg BEFORE INSERT OR UPDATE OR DELETE ON purchase_invoice_lines "
               "FOR EACH ROW EXECUTE FUNCTION purchase_invoice_lines_guard()")


def downgrade() -> None:
    """DESTRUCTIVE for inventory data: use only to roll back this release (take a backup first)."""
    for trg, tbl in (("purchase_invoice_lines_guard_trg", "purchase_invoice_lines"), ("purchase_invoices_guard_trg", "purchase_invoices"),
                     ("supplier_credits_no_change", "supplier_credits"), ("supplier_payments_no_change", "supplier_payments"),
                     ("stock_movements_no_change", "stock_movements")):
        op.execute(f"DROP TRIGGER IF EXISTS {trg} ON {tbl}")
    for fn in ("purchase_invoice_lines_guard", "purchase_invoices_guard", "supplier_money_no_change", "stock_movements_immutable"):
        op.execute(f"DROP FUNCTION IF EXISTS {fn}()")
    op.drop_constraint("ck_part_returns_disposition", "part_returns", type_="check")
    op.drop_column("part_returns", "disposition")
    op.alter_column("part_purchases", "unit_cost", type_=MONEY, existing_type=COST, existing_nullable=False)
    op.drop_constraint("ck_part_purchases_warehouse_item", "part_purchases", type_="check")
    op.drop_constraint("ck_part_purchases_source", "part_purchases", type_="check")
    op.drop_index("ix_part_purchases_inventory_item_id", table_name="part_purchases")
    op.drop_constraint("fk_part_purchases_warehouse", "part_purchases", type_="foreignkey")
    op.drop_constraint("fk_part_purchases_inventory_item", "part_purchases", type_="foreignkey")
    for col in ("issued_qty", "warehouse_id", "inventory_item_id", "source"):
        op.drop_column("part_purchases", col)
    for tbl in ("stock_adjustment_lines", "stock_adjustments", "supplier_credits", "supplier_payments", "goods_receipt_lines", "goods_receipts",
                "purchase_invoice_lines", "purchase_invoices", "stock_reservations", "stock_movements", "inventory_balances",
                "inventory_items", "warehouses", "inventory_categories"):
        op.drop_table(tbl)
