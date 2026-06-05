variable "location" {
  description = "Región de Azure donde se crean los recursos"
  default     = "eastus"
}

variable "prefix" {
  description = "Prefijo para los nombres de recursos (debe ser único en tu suscripción)"
  default     = "supermercado"
}

variable "admin_username" {
  description = "Usuario administrador de las VMs"
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "Contenido de tu clave pública SSH (cat ~/.ssh/id_rsa.pub)"
  type        = string
}

variable "postgres_password" {
  description = "Contraseña del servidor PostgreSQL (mínimo 8 caracteres, mayúsculas, números)"
  type        = string
  sensitive   = true
}

variable "backend_vm_size" {
  description = "Tamaño de la VM del backend (FastAPI + spark-submit driver)"
  default     = "Standard_B4ms"  # 4 vCPU · 16 GB RAM
}

variable "spark_vm_size" {
  description = "Tamaño de la VM de Spark (Master + Worker)"
  default     = "Standard_D4s_v3"  # 4 vCPU · 16 GB RAM
}
