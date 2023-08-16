import frappe
from frappe import _
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    get_ess_settings,
    exception_handler,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_ess_language():
    try:
        ess_settings = get_ess_settings()
        data = []
        for row in ess_settings.get("ess_language"):
            data.append(
                dict(
                    language=row.get("language"),
                    direction=row.get("direction"),
                    language_name=row.get("language_name"),
                )
            )
        return gen_response(200, "Language Get Successfully", data)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_translation(language):
    try:
        if not language:
            return gen_response(500, "Language is required.")

        ess_language_data = frappe.get_value(
            "ESS Language",
            {"language": language},
            ["language"],
            as_dict=1,
        )
        if not ess_language_data:
            return gen_response(500, "Invalid Language.")
        translation_doc = frappe.get_all(
            "Ess Translation",
            filters={"language": language},
            fields=["source_text", "translated_text"],
        )
        translation_data = {}
        for translation in translation_doc:
            translation_data[translation.get("source_text")] = translation.get(
                "translated_text"
            ) or translation.get("source_text")
        return gen_response(
            200,
            "Translation retrieved successfully",
            {
                "translation_data": translation_data,
            },
        )
    except Exception as e:
        return exception_handler(e)
