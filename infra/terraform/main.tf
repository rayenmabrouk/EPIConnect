# Network Security Group for the EPIConnect VM — "port lockdown".
#
#   Public (Internet) : 80 (redirects to HTTPS), 443
#   Admin IP only     : 22 SSH, 8080 Jenkins, 3000 Grafana, 9090 Prometheus
#   Everything else   : denied by Azure's default rules
#                       (port 8000 / Gunicorn is no longer open)
#
# Jenkins needs GitHub's webhook to reach port 8080; GitHub publishes its hook
# IP ranges at https://api.github.com/meta — add them to github_hook_cidrs.

data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

locals {
  github_hook_cidrs = [
    "192.30.252.0/22",
    "185.199.108.0/22",
    "140.82.112.0/20",
    "143.55.64.0/20",
  ]
}

resource "azurerm_network_security_group" "vm" {
  name                = var.nsg_name
  location            = var.location
  resource_group_name = data.azurerm_resource_group.rg.name

  tags = {
    project    = "EPIConnect"
    managed_by = "terraform"
  }
}

resource "azurerm_network_security_rule" "https" {
  name                        = "allow-https"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = "Internet"
  destination_address_prefix  = "*"
  resource_group_name         = data.azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.vm.name
}

resource "azurerm_network_security_rule" "http" {
  name                        = "allow-http"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "80"
  source_address_prefix       = "Internet"
  destination_address_prefix  = "*"
  resource_group_name         = data.azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.vm.name
}

resource "azurerm_network_security_rule" "admin" {
  name                        = "allow-admin-ssh-tools"
  priority                    = 200
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["22", "8080", "3000", "9090"]
  source_address_prefix       = var.admin_ip
  destination_address_prefix  = "*"
  resource_group_name         = data.azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.vm.name
}

resource "azurerm_network_security_rule" "github_webhook" {
  name                        = "allow-github-webhook-jenkins"
  priority                    = 210
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "8080"
  source_address_prefixes     = local.github_hook_cidrs
  destination_address_prefix  = "*"
  resource_group_name         = data.azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.vm.name
}
