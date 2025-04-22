# Copyright 2021 Pierre Verkest
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    is_overtime_due = fields.Boolean(
        string="Is overtime due",
        default=False,
        help="Whether the overtime is due or not. "
        "By default overtime is not due until a manager validates it.",
    )
    validation_sheet_id = fields.Many2one(
        "hr.attendance.validation.sheet",
        string="Validation sheet",
    )

    @api.model_create_multi
    def create(self, vals_list):
        attendances = super().create(vals_list)
        for attendance in attendances:
            if attendance._is_validated_employee_week():
                raise ValidationError(
                    _(
                        "Cannot create new attendance for employee %(employee_name)s. "
                        "Attendance for the day of the check in %(checking_date)s "
                        "has already been reviewed and validated."
                    )
                    % dict(
                        employee_name=attendance.employee_id.name,
                        checking_date=attendance.check_in.date(),
                    )
                )
        return attendances

    def unlink(self, *args, **kwargs):
        for record in self:
            if record.validation_sheet_id.state == "validated":
                raise ValidationError(
                    _(
                        "Can not remove this attendance "
                        "(%(employee_name)s, %(checking_date)s) "
                        "which has been already reviewed and validated."
                    )
                    % dict(
                        employee_name=record.employee_id.name,
                        checking_date=record.check_in.date(),
                    )
                )
        return super().unlink(*args, **kwargs)

    def write(self, *args, **kwargs):
        for record in self:
            if record.validation_sheet_id.state == "validated":
                raise ValidationError(
                    _(
                        "Can not change this attendance "
                        "(%(employee_name)s, %(checking_date)s) "
                        "which has been already reviewed and validated."
                    )
                    % dict(
                        employee_name=record.employee_id.name,
                        checking_date=record.check_in.date(),
                    )
                )
        res = super().write(*args, **kwargs)
        for record in self:
            if record._is_validated_employee_week():
                raise ValidationError(
                    _(
                        "Can not change this attendance "
                        "(%(employee_name)s, %(checking_date)s) "
                        "which would be moved to a validated day."
                    )
                    % dict(
                        employee_name=record.employee_id.name,
                        checking_date=record.check_in.date(),
                    )
                )
        return res

    def _is_validated_employee_week(self):
        validated_week = (
            self.env["hr.attendance.validation.sheet"]
            .with_user(SUPERUSER_ID)
            .search_count(
                [
                    ("employee_id", "=", self.employee_id.id),
                    ("state", "=", "validated"),
                    ("date_from", "<=", self.check_in.date()),
                    ("date_to", ">=", self.check_in.date()),
                ]
            )
        )
        return validated_week > 0

    def _get_attendances_dates(self):
        # Overwriting odoo method to disable
        # HR attendance daily overtime computation
        daily_overtime_attendances = self.filtered(
            lambda att: not att.employee_id.weekly_attendance_validation
        )
        return super(HrAttendance, daily_overtime_attendances)._get_attendances_dates()
