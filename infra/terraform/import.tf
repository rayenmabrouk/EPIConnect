# The NSG was first created by the Azure portal VM wizard. These blocks adopt
# it into Terraform state on the first `terraform apply` instead of trying to
# create a duplicate. Replace <SUBSCRIPTION_ID> before running.
#
# Old portal-created rules (default-allow-ssh, allow-8000, ...) should be
# deleted in the portal or imported the same way, otherwise they stay open.

import {
  to = azurerm_network_security_group.vm
  id = "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/epiconnect-rg/providers/Microsoft.Network/networkSecurityGroups/epiconnect-vm-nsg"
}
