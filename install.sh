#!/bin/bash
set -e  # Exit on error

# Install to system
mkdir -p /usr/local/share/slurm-helper-scripts
cp LICENSE README.md *.py squota /usr/local/share/slurm-helper-scripts/
chown -R root:itscspod /usr/local/share/slurm-helper-scripts
chmod -R 755 /usr/local/share/slurm-helper-scripts

# Create wrapper
tee /usr/local/bin/squota <<'EOF'
#!/bin/bash
exec python3 /usr/local/share/slurm-helper-scripts/squota "$@"
EOF

chmod 755 /usr/local/bin/squota
