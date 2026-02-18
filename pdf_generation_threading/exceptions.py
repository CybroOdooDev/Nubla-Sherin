from odoo.exceptions import UserError


class ReportGenerationPending(UserError):
    """Raised when a report is being generated in background thread."""
    pass