#!/usr/bin/env python3

import html
from iris_interface.IrisModuleInterface import (
    IrisModuleInterface,
    IrisModuleTypes,
    InterfaceStatus,
)
from . import IrisCaseCustomerContactsConfig as interface_conf


def build_case_contact_dropdown(case, logger, iris_api):
    """
    Your original run() function, slightly refactored into a helper.
    """

    # ---- 1. Identify case & customer ----
    cid = case.get("case_id") or case.get("id")
    if not cid:
        logger.error("Could not determine case ID from context.")
        return InterfaceStatus.I2Error(message="No case_id in context.")

    customer = case.get("customer") or {}
    customer_id = customer.get("customer_id")
    if not customer_id:
        logger.warning(f"Case {cid} has no associated customer.")
        return InterfaceStatus.I2Error(message="No customer on this case.")

    logger.info(f"[case={cid}] Loading contacts for customer_id={customer_id}")

    # ---- 2. Fetch contacts for this customer ----
    try:
        # Adjust this endpoint to match your IRIS API
        resp = iris_api.get(f"/customers/{customer_id}/contacts")
        resp.raise_for_status()
        contacts = resp.json()
    except Exception as e:
        logger.error(f"Error while calling /customers/{customer_id}/contacts: {e}")
        return InterfaceStatus.I2Error(message="Could not retrieve contacts from IRIS API.")

    ca = case.get("custom_attributes", {})

    if not contacts:
        logger.info(f"[case={cid}] No contacts for customer_id={customer_id}")
        try:
            ca["Customer contacts"]["Customer contact selector"]["value"] = (
                "<p>No contacts for this customer.</p>"
            )
        except Exception:
            return InterfaceStatus.I2Error(
                message="Custom attributes structure missing (Customer contacts / Customer contact selector)."
            )

        iris_api.patch(f"/cases/{cid}", json={"custom_attributes": ca})
        return InterfaceStatus.I2Success(
            data=case,
            logs=list(logger.handlers),
            message="No contacts found for this customer.",
        )

    # ---- 3. Build HTML <select> for this specific case ----

    # Current selected contact ID
    try:
        current_contact_id = (
            ca
            .get("Customer contacts", {})
            .get("Customer contact ID", {})
            .get("value", "")
        )
    except Exception:
        current_contact_id = ""

    options_html = []
    for c in contacts:
        contact_id = str(c.get("id"))
        name = c.get("name") or c.get("full_name") or "Unnamed"
        email = c.get("email") or ""
        label = f"{name} ({email})" if email else name

        options_html.append(
            f"<option value='{html.escape(contact_id, quote=True)}'>"
            f"{html.escape(label)}</option>"
        )

    options_html_str = "".join(options_html)

    # IMPORTANT:
    # You must inspect the DOM once to get the actual ID of the input
    # backing "Customer contact ID". Temporarily assume:
    hidden_input_dom_id = "inpstd_2_customer_contact_id"

    html_value = f"""
<label>Customer contact</label>
<select class='selectpicker form-control'
        id='select_case_customer_contact'>
    {options_html_str}
</select>

<script>
(function() {{
    var hiddenInputId = '#{hidden_input_dom_id}';

    // Disable manual editing in the form
    $(hiddenInputId).attr('disabled', 'disabled');

    // Existing value (if any)
    var currentVal = $(hiddenInputId).val();

    $('#select_case_customer_contact').selectpicker({{
        liveSearch: true,
        title: 'Select contact',
        style: 'btn-outline-white'
    }});

    if (currentVal) {{
        $('#select_case_customer_contact').val(currentVal);
        $('#select_case_customer_contact').selectpicker('refresh');
    }}

    $('#select_case_customer_contact').on(
        'changed.bs.select',
        function (e, clickedIndex, newValue, oldValue) {{
            var selected = $(e.currentTarget).val();
            $(hiddenInputId).val(selected);
        }}
    );
}})();
</script>
    """.strip()

    try:
        ca.setdefault("Customer contacts", {})
        ca["Customer contacts"].setdefault("Customer contact selector", {})
        ca["Customer contacts"]["Customer contact selector"]["value"] = html_value
    except Exception as e:
        logger.error(f"Error updating custom_attributes structure: {e}")
        return InterfaceStatus.I2Error(
            message="Custom attributes structure does not match expected JSON."
        )

    iris_api.patch(f"/cases/{cid}", json={"custom_attributes": ca})

    logger.info(f"[case={cid}] Contact dropdown updated with {len(contacts)} options.")
    return InterfaceStatus.I2Success(
        data=case,
        logs=list(logger.handlers),
        message=f"Contact dropdown updated with {len(contacts)} contacts.",
    )


class IrisCaseCustomerContacts(IrisModuleInterface):
    # Basic module metadata from config
    _module_name = interface_conf.module_name
    _module_description = interface_conf.module_description
    _interface_version = interface_conf.interface_version
    _module_version = interface_conf.module_version
    _pipeline_support = interface_conf.pipeline_support
    _pipeline_info = interface_conf.pipeline_info
    _module_configuration = interface_conf.module_configuration
    _module_type = interface_conf.module_type

    def register_hooks(self, module_id: int):
        """
        Tell IRIS which hook(s) we want.
        For a manual case processor, use the appropriate case hook.
        """
        # This hook name is illustrative; check your Hooks docs / UI for the
        # exact name IRIS uses when you run a module manually on a case.
        status = self.register_to_hook(
            module_id,
            iris_hook_name="on_manual_case_processor"
        )

        if status.is_failure():
            self.log.error(status.get_message())
        else:
            self.log.info("Subscribed to on_manual_case_processor hook")

    def hooks_handler(self, hook_name: str, data):
        """
        Called by IRIS whenever our hook fires.
        For a manual case processor, `data` will be the case object.
        """
        try:
            result = build_case_contact_dropdown(
                case=data,
                logger=self.log,
                iris_api=self.api,
            )
            return result
        except Exception as e:
            self.log.error(f"Error in Case Customer Contacts module: {e}")
            return InterfaceStatus.I2Error(message=str(e), logs=list(self.message_queue))

