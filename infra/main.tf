# ══════════════════════════════════════════════════════════════════════════════
# Resource Group
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# ══════════════════════════════════════════════════════════════════════════════
# Red Virtual — backend y spark en la misma VNet (comunicación privada)
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_virtual_network" "main" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_subnet" "backend" {
  name                 = "backend-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_subnet" "spark" {
  name                 = "spark-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

# ══════════════════════════════════════════════════════════════════════════════
# Azure Blob Storage — Bucket compartido (dataset + datos procesados)
# Montado en ambas VMs con blobfuse2 en /mnt/data/
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_storage_account" "main" {
  # El nombre debe ser globalmente único, solo minúsculas y números, 3-24 chars
  name                     = "${replace(var.prefix, "-", "")}storage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "data" {
  name                  = "supermercado-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# ══════════════════════════════════════════════════════════════════════════════
# NSG — Backend VM (puertos 22 SSH y 8000 FastAPI)
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_network_security_group" "backend" {
  name                = "${var.prefix}-backend-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "FastAPI"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# NSG — Spark VM (7077 solo desde subnet backend, 8080 Spark UI desde internet)
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_network_security_group" "spark" {
  name                = "${var.prefix}-spark-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "SparkMaster"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "7077"
    source_address_prefix      = "10.0.1.0/24"  # solo desde subnet backend
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "SparkUI"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# Backend VM
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_public_ip" "backend" {
  name                = "${var.prefix}-backend-ip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "backend" {
  name                = "${var.prefix}-backend-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.backend.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.backend.id
  }
}

resource "azurerm_network_interface_security_group_association" "backend" {
  network_interface_id      = azurerm_network_interface.backend.id
  network_security_group_id = azurerm_network_security_group.backend.id
}

resource "azurerm_linux_virtual_machine" "backend" {
  name                = "${var.prefix}-backend-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.backend_vm_size
  admin_username      = var.admin_username

  network_interface_ids = [azurerm_network_interface.backend.id]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init-backend.yaml", {
    storage_account_name = azurerm_storage_account.main.name
    storage_account_key  = azurerm_storage_account.main.primary_access_key
    container_name       = azurerm_storage_container.data.name
    spark_private_ip     = azurerm_network_interface.spark.private_ip_address
    postgres_host        = azurerm_postgresql_flexible_server.main.fqdn
    postgres_password    = var.postgres_password
  }))
}

# ══════════════════════════════════════════════════════════════════════════════
# Spark VM
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_public_ip" "spark" {
  name                = "${var.prefix}-spark-ip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "spark" {
  name                = "${var.prefix}-spark-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.spark.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.spark.id
  }
}

resource "azurerm_network_interface_security_group_association" "spark" {
  network_interface_id      = azurerm_network_interface.spark.id
  network_security_group_id = azurerm_network_security_group.spark.id
}

resource "azurerm_linux_virtual_machine" "spark" {
  name                = "${var.prefix}-spark-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.spark_vm_size
  admin_username      = var.admin_username

  network_interface_ids = [azurerm_network_interface.spark.id]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(templatefile("${path.module}/cloud-init-spark.yaml", {
    storage_account_name = azurerm_storage_account.main.name
    storage_account_key  = azurerm_storage_account.main.primary_access_key
    container_name       = azurerm_storage_container.data.name
  }))
}

# ══════════════════════════════════════════════════════════════════════════════
# PostgreSQL Flexible Server — Base de datos de jobs
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.prefix}-postgres"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = "pgadmin"
  administrator_password = var.postgres_password
  sku_name               = "B_Standard_B1ms"  # 1 vCPU · 2 GB
  storage_mb             = 32768
  backup_retention_days  = 7
  zone                   = "1"
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "supermercado_db"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Permitir conexiones desde la IP pública del backend
resource "azurerm_postgresql_flexible_server_firewall_rule" "backend" {
  name             = "allow-backend"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = azurerm_public_ip.backend.ip_address
  end_ip_address   = azurerm_public_ip.backend.ip_address
}

# ══════════════════════════════════════════════════════════════════════════════
# Azure Static Web App — Frontend React
# ══════════════════════════════════════════════════════════════════════════════

resource "azurerm_static_web_app" "frontend" {
  name                = "${var.prefix}-frontend"
  resource_group_name = azurerm_resource_group.main.name
  # Static Web Apps solo están disponibles en ciertas regiones
  location = "eastus2"
  sku_tier = "Free"
  sku_size = "Free"
}
