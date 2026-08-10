def migrate(cr, version):
    """Add NHS Trust and ward columns before ORM loads to prevent UndefinedColumn errors."""
    cr.execute("""
        ALTER TABLE res_company
            ADD COLUMN IF NOT EXISTS nhs_ods_code       VARCHAR,
            ADD COLUMN IF NOT EXISTS nhs_cqc_number     VARCHAR,
            ADD COLUMN IF NOT EXISTS nhs_trust_type     VARCHAR,
            ADD COLUMN IF NOT EXISTS nhs_trust_region   VARCHAR;
    """)
