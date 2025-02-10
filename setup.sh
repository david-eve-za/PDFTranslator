#!/bin/bash
# Setup script for the PDFTranslator Conda environment

# --- Configuration ---
ENV_NAME="PDFTranslator"
ENV_FILE="environment.yml"

# --- Argument Parsing ---
RECREATE_ENV=false
if [[ "$1" == "--recreate" ]]; then
  RECREATE_ENV=true
fi

# --- Helper Functions ---
print_info() {
  echo "[INFO] $1"
}

print_success() {
  echo "[SUCCESS] $1"
}

print_warning() {
  echo "[WARNING] $1"
}

print_error() {
  echo "[ERROR] $1" >&2 # Print errors to stderr
}

# --- Main Script ---

# 1. Check if conda is installed
print_info "Checking for Conda installation..."
if ! command -v conda &> /dev/null; then
  print_error "Conda is not installed or not found in PATH."
  print_error "Please install Miniconda or Anaconda: https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html"
  exit 1
fi
print_success "Conda found."

# 2. Check if environment file exists
print_info "Checking for environment file: ${ENV_FILE}..."
if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file '${ENV_FILE}' not found in the current directory."
    exit 1
fi
print_success "Environment file found."

# 3. Check/Manage Environment Existence
print_info "Checking if environment '${ENV_NAME}' already exists..."
ENV_EXISTS=false
if conda env list | grep -qE "^${ENV_NAME}\s+"; then
    ENV_EXISTS=true
fi

CREATE_ENV=false # Flag to determine if creation is needed

if $ENV_EXISTS; then
    if $RECREATE_ENV; then
        print_warning "Environment '${ENV_NAME}' exists and --recreate specified. Removing..."
        # Add -y for non-interactive removal
        conda env remove -n "${ENV_NAME}" -y
        if [ $? -ne 0 ]; then
            print_error "Failed to remove existing environment '${ENV_NAME}'. Please remove it manually (conda env remove -n ${ENV_NAME})."
            exit 1
        fi
        print_success "Existing environment '${ENV_NAME}' removed."
        CREATE_ENV=true # Mark for creation after removal
    else
        print_warning "Environment '${ENV_NAME}' already exists. Skipping creation."
        print_info "Use './setup.sh --recreate' to force removal and recreation."
        # Environment exists and we are not recreating, proceed to activation/verification
    fi
else
    # Environment does not exist, needs creation
    CREATE_ENV=true
fi

# 4. Create the environment (if needed)
if $CREATE_ENV; then
    print_info "Creating environment '${ENV_NAME}' from ${ENV_FILE}..."
    conda env create -f "${ENV_FILE}"
    if [ $? -ne 0 ]; then
        print_error "Failed to create environment '${ENV_NAME}'. Check the '${ENV_FILE}' file and conda logs."
        exit 1
    fi
    print_success "Environment '${ENV_NAME}' created successfully."
fi

# 5. Activate the environment (within the script for verification)
# IMPORTANT: This activation is only for the script's execution context.
print_info "Initializing Conda for script execution..."
# Use eval carefully. Ensure conda shell hook output is trusted.
eval "$(conda shell.bash hook)"
if [ $? -ne 0 ]; then
    print_error "Failed to initialize Conda shell hook."
    exit 1
fi

print_info "Activating environment '${ENV_NAME}' for verification..."
conda activate "${ENV_NAME}"
if [ $? -ne 0 ]; then
    print_error "Failed to activate environment '${ENV_NAME}' within the script."
    # Attempt to deactivate if needed, though activate failing might mean it's not active
    conda deactivate &> /dev/null
    exit 1
fi
print_success "Environment activated for script context."


# 6. Verify the installation
print_info "Verifying dependencies using 'pip check'..."
# Use python from the activated env
if python -m pip check; then
    print_success "Dependency check passed."
else
    print_warning "Dependency check reported potential issues. Review the output above."
    # Decide if this should be a fatal error (exit 1) or just a warning
fi

# Deactivate environment at the end of script context
conda deactivate &> /dev/null

# 7. Final Instructions
print_success "Setup script completed."
print_info "--------------------------------------------------"
print_info "To use the environment, run:"
print_info "  conda activate ${ENV_NAME}"
print_info "--------------------------------------------------"
print_info "Remember to grant execute permissions to this script if you haven't already:"
print_info "  chmod +x setup.sh"
print_info "Then run it with:"
print_info "  ./setup.sh"
print_info "To force removal and recreation of the environment, run:"
print_info "  ./setup.sh --recreate"
print_info "--------------------------------------------------"

exit 0