# ------------------------------
# VaultX Password Manager
# Makefile for building, running, and managing the app
# ------------------------------

APP_NAME := vaultx_app.py
VENV := .venv
PYTHON := $(VENV)/bin/python

# Detect OS to handle venv path differences
ifeq ($(OS),Windows_NT)
	PYTHON := $(VENV)/Scripts/python.exe
endif

# ------------------------------
# Targets
# ------------------------------

.PHONY: all setup install run clean backup restore help

# Default: setup & run
all: setup run

# Create virtual environment & install deps
setup:
	@echo "🔧 Setting up virtual environment..."
	python -m venv $(VENV)
	@echo "📦 Installing dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "✅ Setup complete."

# Install dependencies without recreating venv
install:
	$(PYTHON) -m pip install -r requirements.txt

# Run the app
run:
	@echo "🚀 Launching VaultX..."
	$(PYTHON) $(APP_NAME)

# Export a timestamped encrypted backup of vault data
backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@cp -f $$HOME/.vaultx_data/vault.enc backups/vaultx_backup_$$(date +%Y%m%d_%H%M%S).vaultx
	@echo "✅ Backup stored in ./backups"

# Restore a chosen backup file
restore:
	@echo "📂 Available backups:"
	@ls backups/*.vaultx || echo "No backups found."
	@read -p "Enter backup file path to restore: " file; \
	if [ -f $$file ]; then \
	  cp -f $$file $$HOME/.vaultx_data/vault.enc && echo "✅ Restored from $$file"; \
	else echo "❌ Invalid file"; fi

# Remove venv and temp files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV) __pycache__ *.pyc *.pyo backups
	@echo "✅ Clean complete."

# Display available commands
help:
	@echo ""
	@echo "🧭 VaultX Makefile Commands"
	@echo "----------------------------"
	@echo "make setup     - Create venv and install dependencies"
	@echo "make run       - Run the VaultX app"
	@echo "make backup    - Backup encrypted vault"
	@echo "make restore   - Restore from backup"
	@echo "make clean     - Remove venv and temp files"
	@echo "make help      - Show this help message"
	@echo ""
