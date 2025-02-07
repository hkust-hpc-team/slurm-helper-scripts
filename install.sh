#!/bin/bash
set -e  # Exit on error

# Install to system
sudo mkdir -p /usr/local/share/slurm-helper-scripts
sudo cp LICENSE README.md *.py squota /usr/local/share/slurm-helper-scripts/
sudo chown -R root:itscspod /usr/local/share/slurm-helper-scripts
sudo chmod -R 755 /usr/local/share/slurm-helper-scripts

# Create wrapper
sudo tee /usr/local/bin/squota <<'EOF'
#!/bin/bash
exec python3 /usr/local/share/slurm-helper-scripts/squota "$@"
EOF

sudo chmod 755 /usr/local/bin/squota