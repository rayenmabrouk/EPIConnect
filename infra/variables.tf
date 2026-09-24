variable "aws_region" {
  description = "AWS region. AWS Academy Learner Labs only allow us-east-1 and us-west-2."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix for every resource."
  type        = string
  default     = "epiconnect"
}

variable "lab_role_name" {
  description = <<-EOT
    Existing IAM role used as both ECS task role and execution role.
    AWS Academy forbids creating IAM roles, so the pre-provisioned "LabRole" is used there.
    Set to "" in a normal AWS account to create the least-privilege roles in iam.tf instead.
  EOT
  type        = string
  default     = "LabRole"
}

variable "task_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)."
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 512
}

variable "db_instance_class" {
  description = "RDS instance class. Smallest Graviton class; Academy allows nano to medium."
  type        = string
  default     = "db.t4g.micro"
}

variable "image_tag" {
  description = "Image tag written into the Terraform-managed task definition. The pipeline registers new revisions with the real commit tag."
  type        = string
  default     = "bootstrap"
}

variable "alarm_email" {
  description = "Optional e-mail address for CloudWatch alarm notifications (must be confirmed from the inbox)."
  type        = string
  default     = ""
}
