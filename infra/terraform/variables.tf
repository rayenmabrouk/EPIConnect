variable "subscription_id" {
  description = "Azure for Students subscription ID (az account show --query id -o tsv)"
  type        = string
}

variable "resource_group_name" {
  description = "Existing resource group that holds the VM"
  type        = string
  default     = "epiconnect-rg"
}

variable "location" {
  description = "Azure region (Sweden Central is the one allowed by the student subscription policy)"
  type        = string
  default     = "swedencentral"
}

variable "nsg_name" {
  description = "Name of the NSG attached to the VM's NIC (created by the portal wizard)"
  type        = string
  default     = "epiconnect-vm-nsg"
}

variable "admin_ip" {
  description = "Your public IP in CIDR form (curl ifconfig.me)/32 — only this IP can reach SSH and the admin tools"
  type        = string
}
