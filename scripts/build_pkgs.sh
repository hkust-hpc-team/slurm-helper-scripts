#!/usr/bin/env bash
set -euo pipefail

# build_pkgs.sh
# Package a Python wheel into .deb and .rpm using fpm, with metadata read from pyproject.toml.
# Policy per request:
#   - Force PYTHON_BIN=/usr/bin/python3
#   - PREFIX=/usr/local
#   - Validate python version against requires-python (>=3.9)

die() { echo "Error: $*" >&2; exit 1; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Locate pyproject.toml
if [[ -n "${PYPYPROJECT:-}" ]]; then
  PYPROJECT="$PYPYPROJECT"
elif [[ -f "pyproject.toml" ]]; then
  PYPROJECT="$(pwd)/pyproject.toml"
elif [[ -f "$script_dir/pyproject.toml" ]]; then
  PYPROJECT="$script_dir/pyproject.toml"
elif [[ -f "$script_dir/../pyproject.toml" ]]; then
  PYPROJECT="$script_dir/../pyproject.toml"
else
  die "pyproject.toml not found. Run from repo root or set PYPYPROJECT env var."
fi

command -v fpm >/dev/null || die "fpm not found (gem install --no-document fpm)"

# Force system python
PYTHON_BIN="/usr/bin/python3"
command -v "$PYTHON_BIN" >/dev/null || die "Python not found: $PYTHON_BIN"

# Parse pyproject.toml via Python tomllib (3.11+) or tomli fallback.
read_pyproject() {
  "$PYTHON_BIN" - "$PYPROJECT" <<'PY'
import sys, os, re
path = sys.argv[1]
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # Fallback
    except ModuleNotFoundError:
        sys.stderr.write("Missing tomllib/tomli for reading pyproject.toml. Install tomli for this Python.\n")
        sys.exit(2)

with open(path, "rb") as f:
    data = tomllib.load(f)

prj = data.get("project", {}) or {}
name = prj.get("name") or ""
version = prj.get("version") or ""
description = prj.get("description") or ""
requires_python = prj.get("requires-python") or ""

authors = prj.get("authors") or []
maintainer = ""
vendor = ""
if authors:
    a = authors[0]
    if isinstance(a, dict):
        n = a.get("name") or ""
        e = a.get("email") or ""
        if n and e:
            maintainer = f"{n} <{e}>"
        else:
            maintainer = n or e or ""
        vendor = n or ""
    elif isinstance(a, str):
        maintainer = a
        vendor = a

lic = prj.get("license")
license_str = ""
if isinstance(lic, str):
    license_str = lic
elif isinstance(lic, dict):
    if isinstance(lic.get("text"), str):
        license_str = lic["text"].strip().splitlines()[0]
    elif isinstance(lic.get("file"), str):
        license_str = os.path.basename(lic["file"])

def normalize_for_wheel(n: str) -> str:
    return re.sub(r"[-_.]+", "_", n).lower()

distname = normalize_for_wheel(name)

def shquote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

print(f"PKGNAME={shquote(name)}")
print(f"DISTNAME={shquote(distname)}")
print(f"VERSION={shquote(version)}")
print(f"DESCRIPTION={shquote(description)}")
print(f"MAINTAINER={shquote(maintainer)}")
print(f"LICENSE={shquote(license_str)}")
print(f"VENDOR={shquote(vendor or maintainer.split('<')[0].strip() or name)}")
print(f"REQUIRES_PYTHON={shquote(requires_python)}")
PY
}

eval "$(read_pyproject)" || die "Failed to parse $PYPROJECT"

[[ -n "$PKGNAME" ]] || die "project.name missing in $PYPROJECT"
[[ -n "$VERSION" ]] || die "project.version missing in $PYPROJECT"

# Validate python version against requires-python lower bound (e.g., ">=3.9")
if [[ -n "${REQUIRES_PYTHON:-}" ]]; then
  req_min=""

  # 提取第一個形如 ">=X.Y" 的片段，安全起見用純字串運算
  rp="$REQUIRES_PYTHON"
  # 移除空白
  rp="${rp//[[:space:]]/}"
  # 找到 ">=" 的位置
  if [[ "$rp" == *">="* ]]; then
    tail="${rp#*>=}"
    # 取出開頭的數字點數字（X.Y 或 X.Y.Z）
    if [[ "$tail" =~ ^([0-9]+\.[0-9]+) ]]; then
      req_min="${BASH_REMATCH[1]}"
    fi
  fi

  if [[ -n "$req_min" ]]; then
    py_ver="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
    # 版本比較：ver_ge a b → b >= a ?
    ver_ge() { printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1 | grep -qx "$1"; }
    ver_ge "$req_min" "$py_ver" || die "Python at $PYTHON_BIN is $py_ver, but requires-python is $REQUIRES_PYTHON"
  fi
fi

# Resolve wheel file (prefer py3-none-any)
shopt -s nullglob
candidates=( "dist/${DISTNAME}-${VERSION}-"*.whl )
(( ${#candidates[@]} > 0 )) || die "No wheel found matching dist/${DISTNAME}-${VERSION}-*.whl. Build it first (e.g., $PYTHON_BIN -m build)."
WHEEL=""
for c in "${candidates[@]}"; do
  if [[ "$c" == *"-any.whl" ]]; then WHEEL="$c"; break; fi
done
WHEEL="${WHEEL:-${candidates[0]}}"

echo "Using:"
echo "  pyproject: $PYPROJECT"
echo "  name:      $PKGNAME"
echo "  version:   $VERSION"
echo "  license:   ${LICENSE:-"(none)"}"
echo "  maintainer:${MAINTAINER:-"(none)"}"
echo "  vendor:    ${VENDOR:-"(none)"}"
echo "  requires:  ${REQUIRES_PYTHON:-"(unspecified)"}"
echo "  wheel:     $WHEEL"
echo "  python:    $PYTHON_BIN"
echo "  prefix:    /usr/local"

# Ensure pip exists for this Python
"$PYTHON_BIN" -m pip --version >/dev/null 2>&1 || die "pip for $PYTHON_BIN not found"

PREFIX="/usr/local"

ROOT="$(mktemp -d)"
cleanup() {
  if [[ "${KEEP_ROOT:-0}" != "1" ]]; then
    rm -rf "$ROOT"
  else
    echo "Keeping staging dir: $ROOT"
  fi
}
trap cleanup EXIT

# Install wheel into staging root; this creates $ROOT/$PREFIX/{bin,lib/...}
"$PYTHON_BIN" -m pip install --no-deps --no-compile --root "$ROOT" --prefix "$PREFIX" "$WHEEL"

# Force console_scripts shebang to /usr/bin/python3 (avoid conda/venv path bleeding)
for bindir in "$ROOT/usr/local/bin" "$ROOT/usr/bin"; do
  if [[ -d "$bindir" ]]; then
    for f in "$bindir"/*; do
      [[ -f "$f" ]] || continue
      if head -n1 "$f" | grep -q '^#!'; then
        sed -i '1s|^#!.*$|#!/usr/bin/python3|' "$f"
      fi
    done
  fi
done

COMMON_META=(
  --license "$LICENSE"
  --maintainer "$MAINTAINER"
  --vendor "$VENDOR"
  --description "$DESCRIPTION"
  --iteration "${ITERATION:-1}"
)

# Per fpm docs, set architecture with -a/--architecture. Use 'all' for pure Python.
ARCH="${ARCH:-all}"

# Build DEB
fpm -s dir -t deb \
  -n "$PKGNAME" \
  -v "$VERSION" \
  -a "$ARCH" \
  -C "$ROOT" \
  "${COMMON_META[@]}" \
  "usr/local/"

# Build RPM
fpm -s dir -t rpm \
  -n "$PKGNAME" \
  -v "$VERSION" \
  -a "$ARCH" \
  -C "$ROOT" \
  "${COMMON_META[@]}" \
  "usr/local/"

echo "Done. Generated packages:"
ls -lh ./*.deb ./*.rpm 2>/dev/null || true

# Helpful hint: /usr/local on RHEL-like may not be in Python's default sys.path for site-packages.
echo "Note: Modules are installed under /usr/local/lib/pythonX.Y/site-packages."
echo "      Ensure the runtime python (/usr/bin/python3) includes that path (it may not on some distros; if not, consider PREFIX=/usr)."