# iris_case_customer_contacts/IrisCaseCustomerContactsConfig.py
from iris_interface.IrisModuleInterface import IrisModuleTypes

module_name = "Case Customer Contacts"
module_description = "Builds a per-case customer contact dropdown."
interface_version = 1.2      # match your iris_interface version
module_version = 1.0

# This is a processor module
module_type = IrisModuleTypes.module_processor

# No pipeline for this one
pipeline_support = False
pipeline_info = {}

# Optional params you can configure in the UI (nice to have, but simple)
module_configuration = [
    {
        "param_name": "contacts_endpoint",
        "param_human_name": "Contacts endpoint template",
        "param_description": "IRIS API path to list contacts for a customer. Use {customer_id} placeholder.",
        "default": "/customers/{customer_id}/contacts",
        "mandatory": True,
        "type": "string"
    },
    {
        "param_name": "hidden_input_dom_id",
        "param_human_name": "Hidden input DOM ID",
        "param_description": "DOM id of the 'Customer contact ID' input element (inspect it in the browser).",
        "default": "inpstd_2_customer_contact_id",
        "mandatory": True,
        "type": "string"
    }
]
