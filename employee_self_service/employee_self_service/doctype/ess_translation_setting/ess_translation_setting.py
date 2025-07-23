# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import os

from rq.timeouts import JobTimeoutException

import frappe
from frappe import _

from employee_self_service.employee_self_service.doctype.ess_translation_setting.importer import (
    Importer,
)
from employee_self_service.employee_self_service.doctype.ess_translation_setting.exporter import (
    Exporter,
)
from frappe.model.document import Document
from frappe.utils.scheduler import is_scheduler_inactive
from frappe.modules.import_file import import_file_by_path
from frappe.utils.background_jobs import enqueue, is_job_enqueued
from frappe.utils.csvutils import validate_google_sheets_url


class ESSTranslationSetting(Document):
    from typing import TYPE_CHECKING, Literal

    if TYPE_CHECKING:
        from types import DF

        custom_delimiters: DF.Check
        # delimiter_options: DF.Data | None
        google_sheets_url: DF.Data | None
        import_file: DF.Attach | None
        import_type: Literal["", "Insert New Records", "Update Existing Records"]
        payload_count: DF.Int
        show_failed_logs: DF.Check
        status: Literal["Pending", "Success", "Partial Success", "Error", "Timed Out"]
        template_options: DF.Code | None
        template_warnings: DF.Code | None
        # use_csv_sniffer: DF.Check

    def validate(self):
        doc_before_save = self.get_doc_before_save()
        if (
            not (self.import_file or self.google_sheets_url)
            or (doc_before_save and doc_before_save.import_file != self.import_file)
            or (
                doc_before_save
                and doc_before_save.google_sheets_url != self.google_sheets_url
            )
        ):
            self.template_options = "{}"
            self.template_warnings = ""

        # self.set_delimiters_flag()
        self.validate_import_file()
        self.validate_google_sheets_url()
        self.set_payload_count()

    # def set_delimiters_flag(self):
    #     if self.import_file:
    #         frappe.flags.delimiter_options = self.get("delimiter_options") or ","

    def validate_import_file(self):
        if self.import_file:
            # validate template
            self.get_importer()

    def validate_google_sheets_url(self):
        if not self.google_sheets_url:
            return
        validate_google_sheets_url(self.google_sheets_url)

    def set_payload_count(self):
        if self.import_file:
            i = self.get_importer()
            payloads = i.import_file.get_payloads_for_import()
            self.payload_count = len(payloads)

    @frappe.whitelist()
    def get_preview_from_template(self, import_file=None, google_sheets_url=None):
        if import_file:
            self.import_file = import_file
            # self.set_delimiters_flag()

        if google_sheets_url:
            self.google_sheets_url = google_sheets_url

        if not (self.import_file or self.google_sheets_url):
            return

        i = self.get_importer()
        return i.get_data_for_import_preview()

    def start_import(self):
        run_now = frappe.conf.developer_mode
        if is_scheduler_inactive() and not run_now:
            frappe.throw(
                _("Scheduler is inactive. Cannot import data."),
                title=_("Scheduler Inactive"),
            )

        job_id = f"ess_translation_setting||{self.name}"

        if not is_job_enqueued(job_id):
            enqueue(
                start_import,
                queue="default",
                timeout=10000,
                event="ess_translation_setting",
                job_id=job_id,
                ess_translation_setting=self.name,
                now=run_now,
            )
            return True

        return False

    def export_errored_rows(self):
        return self.get_importer().export_errored_rows()

    def download_import_log(self):
        return self.get_importer().export_import_log()

    def get_importer(self):
        return Importer(
            "ESS Translation Request",
            ess_translation_setting=self,
            # use_sniffer=self.use_csv_sniffer,
        )

    def on_trash(self):
        frappe.db.delete(
            "ESS Translation Request Log", {"ess_translation_request": self.name}
        )


@frappe.whitelist()
def get_preview_from_template(
    ess_translation_setting: str,
    import_file: str | None = None,
    google_sheets_url: str | None = None,
):
    di: ESSTranslationSetting = frappe.get_doc(
        "ESS Translation Setting", ess_translation_setting
    )
    di.check_permission("read")
    return di.get_preview_from_template(import_file, google_sheets_url)


@frappe.whitelist()
def form_start_import(ess_translation_setting: str):
    di: ESSTranslationSetting = frappe.get_doc(
        "ESS Translation Setting", ess_translation_setting
    )
    di.check_permission("write")
    return di.start_import()


def start_import(ess_translation_setting):
    """This method runs in background job"""
    ess_translation_setting = frappe.get_doc(
        "ESS Translation Setting", ess_translation_setting
    )
    try:
        i = Importer(
            "ESS Translation Request",
            ess_translation_setting=ess_translation_setting,
        )
        i.import_data()
    except JobTimeoutException:
        frappe.db.rollback()
        ess_translation_setting.db_set("status", "Timed Out")
    except Exception:
        frappe.db.rollback()
        ess_translation_setting.db_set("status", "Error")
        ess_translation_setting.log_error("Data import failed")
    finally:
        frappe.flags.in_import = False

    frappe.publish_realtime(
        "ess_translation_setting_refresh",
        {"ess_translation_setting": ess_translation_setting.name},
    )


@frappe.whitelist()
def download_template(
    doctype,
    export_fields=None,
    export_records=None,
    export_filters=None,
    file_type="CSV",
):
    """
    Download template from Exporter.
    """
    frappe.has_permission(doctype, "read", throw=True)

    export_fields = frappe.parse_json(export_fields)
    export_filters = frappe.parse_json(export_filters) or {}
    export_data = export_records != "blank_template"

    # Custom logic only for ESS Translation
    if doctype == "ESS Translation":
        # Get destination_language from filters
        destination_language = export_filters.get("destination_language")

        if not destination_language:
            frappe.throw(
                _("Destination Language is required for exporting ESS Translations.")
            )

        # Get all ESS Word names
        ess_words = frappe.get_all("ESS Word", pluck="name")

        # Apply filter: where `ess_word` in ESS Translation and matches destination language
        export_filters.update(
            {
                "ess_word": ["in", ess_words],
                "destination_language": destination_language,
            }
        )

    e = Exporter(
        doctype,
        export_fields=export_fields,
        export_data=export_data,
        export_filters=export_filters,
        file_type=file_type,
        export_page_length=5 if export_records == "5_records" else None,
    )
    e.build_response()


@frappe.whitelist()
def download_errored_template(ess_translation_setting: str):
    ess_translation_setting: ESSTranslationSetting = frappe.get_doc(
        "ESS Translation Setting", ess_translation_setting
    )
    ess_translation_setting.check_permission("read")
    ess_translation_setting.export_errored_rows()


@frappe.whitelist()
def download_import_log(ess_translation_setting: str):
    ess_translation_setting: ESSTranslationSetting = frappe.get_doc(
        "ESS Translation Setting", ess_translation_setting
    )
    ess_translation_setting.check_permission("read")
    ess_translation_setting.download_import_log()


@frappe.whitelist()
def get_import_status(ess_translation_setting: str):
    ess_translation_setting: ESSTranslationSetting = frappe.get_doc(
        "ESS Translation Setting", ess_translation_setting
    )
    ess_translation_setting.check_permission("read")

    import_status = {"status": ess_translation_setting.status}
    logs = frappe.get_all(
        "ESS Translation Request Log",
        fields=["count(*) as count", "success"],
        filters={"ess_translation_request": ess_translation_setting},
        group_by="success",
    )

    total_payload_count = ess_translation_setting.payload_count

    for log in logs:
        if log.get("success"):
            import_status["success"] = log.get("count")
        else:
            import_status["failed"] = log.get("count")

    import_status["total_records"] = total_payload_count

    return import_status


@frappe.whitelist()
def get_import_logs(ess_translation_setting: str):
    doc = frappe.get_doc("ESS Translation Setting", ess_translation_setting)
    doc.check_permission("read")

    return frappe.get_all(
        "ESS Translation Request Log",
        fields=["success", "docname", "messages", "exception", "row_indexes"],
        filters={"ess_translation_request": ess_translation_setting},
        limit_page_length=5000,
        order_by="log_index",
    )


def import_file(
    doctype, file_path, import_type, submit_after_import=False, console=False
):
    """
    Import documents in from CSV or XLSX using data import.

    :param doctype: DocType to import
    :param file_path: Path to .csv, .xls, or .xlsx file to import
    :param import_type: One of "Insert" or "Update"
    :param submit_after_import: Whether to submit documents after import
    :param console: Set to true if this is to be used from command line. Will print errors or progress to stdout.
    """

    data_import = frappe.new_doc("ESS Translation Setting")
    data_import.submit_after_import = submit_after_import
    data_import.import_type = (
        "Insert New Records"
        if import_type.lower() == "insert"
        else "Update Existing Records"
    )

    i = Importer(
        doctype=doctype, file_path=file_path, data_import=data_import, console=console
    )
    i.import_data()


def import_doc(path, pre_process=None, sort=False):
    if os.path.isdir(path):
        files = [os.path.join(path, f) for f in os.listdir(path)]
        if sort:
            files.sort()
    else:
        files = [path]

    for f in files:
        if f.endswith(".json"):
            frappe.flags.mute_emails = True
            import_file_by_path(
                f,
                data_import=True,
                force=True,
                pre_process=pre_process,
                reset_permissions=True,
            )
            frappe.flags.mute_emails = False
            frappe.db.commit()
        else:
            raise NotImplementedError("Only .json files can be imported")


def export_json(
    doctype, path, filters=None, or_filters=None, name=None, order_by="creation asc"
):
    def post_process(out):
        # Note on Tree DocTypes:
        # The tree structure is maintained in the database via the fields "lft"
        # and "rgt". They are automatically set and kept up-to-date. Importing
        # them would destroy any existing tree structure. For this reason they
        # are not exported as well.
        del_keys = ("modified_by", "creation", "owner", "idx", "lft", "rgt")
        for doc in out:
            for key in del_keys:
                if key in doc:
                    del doc[key]
            for v in doc.values():
                if isinstance(v, list):
                    for child in v:
                        for key in (
                            *del_keys,
                            "docstatus",
                            "doctype",
                            "modified",
                            "name",
                            "parent",
                            "parentfield",
                            "parenttype",
                        ):
                            if key in child:
                                del child[key]

    out = []
    if name:
        out.append(frappe.get_doc(doctype, name).as_dict())
    elif frappe.db.get_value("DocType", doctype, "issingle"):
        out.append(frappe.get_doc(doctype).as_dict())
    else:
        for doc in frappe.get_all(
            doctype,
            fields=["name"],
            filters=filters,
            or_filters=or_filters,
            limit_page_length=0,
            order_by=order_by,
        ):
            out.append(frappe.get_doc(doctype, doc.name).as_dict())
    post_process(out)

    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        path = os.path.join("..", path)

    with open(path, "w") as outfile:
        outfile.write(frappe.as_json(out, ensure_ascii=False))


def export_csv(doctype, path):
    from frappe.core.doctype.data_export.exporter import export_data

    with open(path, "wb") as csvfile:
        export_data(doctype=doctype, all_doctypes=True, template=True, with_data=True)
        csvfile.write(frappe.response.result.encode("utf-8"))
