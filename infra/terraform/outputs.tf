output "nsg_id" {
  value = azurerm_network_security_group.vm.id
}

output "open_ports" {
  value = {
    public = ["80", "443"]
    admin  = ["22", "8080", "3000", "9090"]
  }
}
