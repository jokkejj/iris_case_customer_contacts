# iris_case_customer_contacts/IrisCaseCustomerContactsConfig.py
from iris_interface.IrisModuleInterface import IrisModuleTypes

module_name = "Case Customer Contacts"
module_description = "Builds a per-case customer contact dropdown."
interface_version = 2.4.25      # match your iris_interface version
module_version = 1.0

module_type = IrisModuleTypes.module_processor
pipeline_support = False
pipeline_info = {}

# No special parameters for now
module_configuration = []

