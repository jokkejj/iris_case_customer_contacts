#!/usr/bin/env python3

import html

from iris_interface.IrisModuleInterface import (
    IrisModuleInterface,
    InterfaceStatus,
)
from . import IrisCaseCustomerContactsConfig as interface_conf


# Names of your custom attribute group & fields in the Case custom attributes JSON
CUSTOM_ATTR_GROUP = "Customer contacts"
CUSTOM_ATTR_DROPDOWN = "Customer contact selector"
CUSTOM_ATTR_HIDDEN_ID = "Customer contact ID"


def build_case_contact_dropdown(case, module):
    """
    Core logic: fetch contacts for this case's customer, build HTML dropdown,
    and update custom attributes on the case.
    """

    log = module.log
    iris_api = module.api

    # --- 1. Identify case & customer ---

    cid = case.get("case_id") or case.get("id")
    if not cid:
        log.error("No case_id / id found in case data.")
        return

    customer = case.get("customer") or {}
    customer_id = customer.get("customer_id")
    if not customer_id:
        log.warning(f"[Case {cid}] No customer assigned, cannot build contact dropdown.")
        return

    log.info(f"[Case {cid}] Building contact dropdown for customer_id={customer_id}")

    # Contacts endpoint template comes from module configuration
    contacts_endpoint_tmpl = module._dict_conf.get(
        "contacts_endpoint",
        "/customers/{customer_id}/contacts"
    )
    endpoint = contacts_endpoint_tmpl.format(customer_id=customer_id)

    # --- 2. Fetch contacts for this customer ---

    try:
        resp = iris_api.get(endpoint)
        resp.raise_for_status()
        contacts = resp.json()
    except Exception as e:
        log.error(f"[Case {cid}] Error calling {endpoint}: {e}")
        return

    # Get custom attributes dict (copy reference; IRIS expects same structure back)
    ca = case.get("custom_attributes") or {}

    # Ensure our group/fields exist in the dict
    ca.setdefault(CUSTOM_ATTR_GROUP, {})
    ca[CUSTOM_ATTR_GROUP].setdefault(CUSTOM_ATTR_DROPDOWN, {"value": ""})
    ca[CUSTOM_ATTR_GROUP].setdefault(CUSTOM_ATTR_HIDDEN_ID, {"value": ""})

    # If no contacts, show message and clear dropdown
    if not contacts:
        log.info(f"[Case {cid}] No contacts for customer_id={customer_id}")
        ca[CUSTOM_ATTR_GROUP][CUSTOM_ATTR_DROPDOWN]["value"] = (
            "<p>No contacts for this customer.</p>"
        )
        try:
            iris_api.patch(f"/cases/{cid}", json={"custom_attributes": ca})
        except Exception as e:
            log.error(f"[Case {cid}] Error updating case custom_attributes: {e}")
        return

    # --- 3. Build HTML <select> with options ---

    # Read current stored contact ID (hidden field)
    current_contact_id = ca[CUSTOM_ATTR_GROUP][CUSTOM_ATTR_HIDDEN_ID].get("value") or ""

    # Build <option> elements
    options_html = []
    for c in contacts:
        contact_id = str(c.get("id"))
        # adapt these keys to your contacts schema
        name = c.get("name") or c.get("full_name") or "Unnamed"
        email = c.get("email") or ""
        label = f"{name} ({email})" if email else name

        options_html.append(
            f"<option value='{html.escape(contact_id, quote=True)}'>"
            f"{html.escape(label)}</option>"
        )

    options_html_str = "".join(options_html)

    # Hidden input DOM ID from module configuration
    hidden_input_dom_id = module._dict_conf.get(
        "hidden_input_dom_id",
        "inpstd_2_customer_contact_id"  # you will update this after inspecting
    )

    # HTML & JS injected into the HTML custom attribute
    html_value = f"""
<label>Customer contact</label>
<select class='selectpicker form-control'
        id='select_case_customer_contact'>
    {options_html_str}
</select>

<script>
(function() {{
    var hiddenInputId = '#{hidden_input_dom_id}';

    // Protect hidden field from manual typing
    $(hiddenInputId).attr('disabled', 'disabled');

    // Existing value (if any)
    var currentVal = $(hiddenInputId).val();

    // Initialize bootstrap selectpicker
    $('#select_case_customer_contact').selectpicker({{
        liveSearch: true,
        title: 'Select contact',
        style: 'btn-outline-white'
    }});

    // Restore previous selection if there is one
    if (currentVal) {{
        $('#select_case_customer_contact').val(currentVal);
        $('#select_case_customer_contact').selectpicker('refresh');
    }}

    // Keep hidden field in sync with selected contact ID
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

    # Set the generated HTML into our HTML custom attribute
    ca[CUSTOM_ATTR_GROUP][CUSTOM_ATTR_DROPDOWN]["value"] = html_value

    # --- 4. Push updated custom attributes back to the case ---

    try:
        iris_api.patch(f"/cases/{cid}", json={"custom_attributes": ca})
    except Exception as e:
        log.error(f"[Case {cid}] Error updating case custom_attributes: {e}")
        return

    log.info(f"[Case {cid}] Contact dropdown updated with {len(contacts)} contacts.")


class IrisCaseCustomerContacts(IrisModuleInterface):
    """
    Processor module:
    - Subscribes to on_manual_trigger_case
    - When triggered on a case, it builds / refreshes the Case's customer contact dropdown.
    """

    # config from config file
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
        Called by IRIS when it's time to subscribe to hooks.
        We subscribe to the manual case trigger: on_manual_trigger_case
        """
        status = self.register_to_hook(
            module_id,
            iris_hook_name="on_manual_trigger_case"
        )

        if status.is_failure():
            self.log.error(status.get_message())
        else:
            self.log.info("Successfully subscribed to on_manual_trigger_case hook")

        # If you ALSO want it to run automatically when cases are updated,
        # you can optionally subscribe to this second hook:
        #
        # auto_status = self.register_to_hook(
        #     module_id,
        #     iris_hook_name="on_postload_case_update"
        # )
        # if auto_status.is_failure():
        #     self.log.error(auto_status.get_message())
        # else:
        #     self.log.info("Successfully subscribed to on_postload_case_update hook")

    def hooks_handler(self, hook_name: str, data):
        """
        Called each time one of our hooks is triggered.

        For on_manual_trigger_case, `data` is the case object.
        """
        self.log.info(f"Case Customer Contacts module received hook {hook_name}")

        try:
            # Only handle case-related hooks here
            if hook_name in ("on_manual_trigger_case", "on_postload_case_update"):
                build_case_contact_dropdown(case=data, module=self)
        except Exception as e:
            self.log.error(f"Error in Case Customer Contacts module: {e}")

        # Always return success with (possibly updated) data
        return InterfaceStatus.I2Success(data=data, logs=list(self.message_queue))
