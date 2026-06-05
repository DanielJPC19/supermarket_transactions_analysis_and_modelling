output "backend_public_ip" {
  description = "IP pública de la VM del backend — úsala en VITE_API_URL y ALLOWED_ORIGINS"
  value       = azurerm_public_ip.backend.ip_address
}

output "spark_public_ip" {
  description = "IP pública de la VM de Spark — para conectarte via SSH"
  value       = azurerm_public_ip.spark.ip_address
}

output "spark_private_ip" {
  description = "IP privada de la VM de Spark — va en SPARK_MASTER_URL del backend"
  value       = azurerm_network_interface.spark.private_ip_address
}

output "spark_master_url" {
  description = "Valor listo para pegar en SPARK_MASTER_URL del .env del backend"
  value       = "spark://${azurerm_network_interface.spark.private_ip_address}:7077"
}

output "postgres_host" {
  description = "FQDN del servidor PostgreSQL — va en POSTGRES_HOST del .env"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgres_connection_info" {
  description = "Información de conexión PostgreSQL"
  value = {
    host     = azurerm_postgresql_flexible_server.main.fqdn
    port     = 5432
    user     = "pgadmin"
    database = "supermercado_db"
  }
}

output "storage_account_name" {
  description = "Nombre de la cuenta de storage (para az storage blob upload-batch)"
  value       = azurerm_storage_account.main.name
}

output "storage_account_key" {
  description = "Clave de acceso al storage (sensible)"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "storage_container_name" {
  description = "Nombre del container de datos"
  value       = azurerm_storage_container.data.name
}

output "frontend_url" {
  description = "URL del Static Web App — va en ALLOWED_ORIGINS del .env del backend"
  value       = "https://${azurerm_static_web_app.frontend.default_host_name}"
}

output "static_web_app_api_key" {
  description = "API key para desplegar el frontend con az staticwebapp upload"
  value       = azurerm_static_web_app.frontend.api_key
  sensitive   = true
}

output "ssh_backend" {
  description = "Comando SSH para conectarte al backend"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.backend.ip_address}"
}

output "ssh_spark" {
  description = "Comando SSH para conectarte al Spark"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.spark.ip_address}"
}

output "spark_ui_url" {
  description = "URL de la interfaz web de Spark"
  value       = "http://${azurerm_public_ip.spark.ip_address}:8080"
}
