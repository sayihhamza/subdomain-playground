#!/usr/bin/env bash
#
# Automated build script for Go-based security tools
# Builds: subfinder, httpx, dnsx, subzy, nuclei
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${PROJECT_ROOT}/bin"
GO_BIN="/opt/homebrew/bin/go"

# Tool directories (tool_name:main_file)
TOOLS=(
    "subfinder:cmd/subfinder/main.go"
    "httpx:cmd/httpx/httpx.go"
    "dnsx:cmd/dnsx/dnsx.go"
    "subzy:main.go"
    "nuclei:cmd/nuclei/main.go"
)

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_go() {
    if [ ! -f "$GO_BIN" ]; then
        log_error "Go not found at $GO_BIN"
        exit 1
    fi

    GO_VERSION=$($GO_BIN version | awk '{print $3}')
    log_info "Using Go: $GO_VERSION"
}

create_bin_dir() {
    mkdir -p "$BIN_DIR"
    log_info "Binary directory: $BIN_DIR"
}

build_tool() {
    local tool_name=$1
    local main_file=$2
    local tool_dir="${PROJECT_ROOT}/${tool_name}"

    log_info "Building $tool_name..."

    if [ ! -d "$tool_dir" ]; then
        log_error "Tool directory not found: $tool_dir"
        return 1
    fi

    cd "$tool_dir"

    # Check if go.mod exists
    if [ ! -f "go.mod" ]; then
        log_error "go.mod not found in $tool_dir"
        return 1
    fi

    # Download dependencies
    log_info "Downloading dependencies for $tool_name..."
    $GO_BIN mod download 2>&1 | grep -v "^go: downloading" || true

    # Build the tool
    OUTPUT_PATH="${BIN_DIR}/${tool_name}"

    log_info "Compiling $tool_name..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS build
        $GO_BIN build -v -ldflags="-s -w" -o "$OUTPUT_PATH" "$main_file" 2>&1 | tail -1 || true
    else
        # Linux build (static)
        $GO_BIN build -v -ldflags="-s -w -extldflags '-static'" -o "$OUTPUT_PATH" "$main_file" 2>&1 | tail -1 || true
    fi

    if [ $? -eq 0 ] && [ -f "$OUTPUT_PATH" ]; then
        log_info "✓ Built $tool_name successfully"
        chmod +x "$OUTPUT_PATH"

        # Verify binary
        if "$OUTPUT_PATH" -version 2>/dev/null || "$OUTPUT_PATH" version 2>/dev/null || "$OUTPUT_PATH" -h > /dev/null 2>&1; then
            log_info "✓ Binary verification passed for $tool_name"
        else
            log_warn "Binary built but verification command failed (this may be normal)"
        fi

        return 0
    else
        log_error "✗ Failed to build $tool_name"
        return 1
    fi
}

build_all() {
    local failed=()
    local succeeded=()

    log_info "Starting build process for all tools..."
    echo ""

    for tool_spec in "${TOOLS[@]}"; do
        IFS=':' read -r tool_name main_file <<< "$tool_spec"

        if build_tool "$tool_name" "$main_file"; then
            succeeded+=("$tool_name")
        else
            failed+=("$tool_name")
        fi

        echo ""
    done

    # Summary
    echo "========================================"
    log_info "Build Summary:"
    echo "========================================"

    if [ ${#succeeded[@]} -gt 0 ]; then
        log_info "Successfully built (${#succeeded[@]}):"
        for tool in "${succeeded[@]}"; do
            echo "  ✓ $tool"
        done
    fi

    if [ ${#failed[@]} -gt 0 ]; then
        log_error "Failed to build (${#failed[@]}):"
        for tool in "${failed[@]}"; do
            echo "  ✗ $tool"
        done
        echo ""
        log_error "Build completed with errors"
        exit 1
    else
        echo ""
        log_info "All tools built successfully!"
        log_info "Binaries location: $BIN_DIR"
    fi
}

# Main execution
main() {
    echo "========================================"
    log_info "Go Tool Builder v1.0.0"
    echo "========================================"
    echo ""

    check_go
    create_bin_dir
    build_all

    echo ""
    log_info "Build process completed!"
}

main
