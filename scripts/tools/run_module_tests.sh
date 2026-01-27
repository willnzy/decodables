#!/bin/bash
# Run integration tests by module
# Usage: ./run_module_tests.sh <module_name> [pytest_args]
#
# Examples:
#   ./run_module_tests.sh projects
#   ./run_module_tests.sh billing -v
#   ./run_module_tests.sh webhooks --tb=short
#   ./run_module_tests.sh all  # Run all modules

set -e

STAGING_DIR="tests/integration/staging"

# Available modules
MODULES=(
    "assets"
    "billing"
    "campaigns"
    "cascade_delete"
    "config"
    "events"
    "folders"
    "projects"
    "soft_delete"
    "system_resources"
    "tags"
    "templates"
    "themes"
    "tier_enforcement"
    "users"
    "webhooks"
    "workspaces"
)

show_help() {
    echo "Usage: $0 <module_name> [pytest_args]"
    echo ""
    echo "Available modules:"
    for module in "${MODULES[@]}"; do
        echo "  - $module"
    done
    echo "  - all (run all modules)"
    echo "  - list (show all modules with test counts)"
    echo ""
    echo "Examples:"
    echo "  $0 projects           # Run projects tests"
    echo "  $0 billing -v         # Run billing tests with verbose"
    echo "  $0 webhooks --tb=short"
    echo "  $0 all -m p0          # Run all P0 tests"
    echo "  $0 list               # List modules with test counts"
}

list_modules() {
    echo "Module Test Counts:"
    echo "==================="
    total=0
    for module in "${MODULES[@]}"; do
        if [ -d "$STAGING_DIR/$module" ]; then
            count=$(python -m pytest "$STAGING_DIR/$module" --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1 || echo "0")
            printf "  %-20s %s tests\n" "$module" "$count"
            total=$((total + count))
        fi
    done
    echo "==================="
    echo "Total: $total tests"
}

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

MODULE=$1
shift  # Remove first argument, rest are pytest args

case $MODULE in
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    "list")
        list_modules
        exit 0
        ;;
    "all")
        echo "Running all integration tests..."
        python -m pytest "$STAGING_DIR" "$@"
        ;;
    *)
        if [ -d "$STAGING_DIR/$MODULE" ]; then
            echo "Running $MODULE tests..."
            python -m pytest "$STAGING_DIR/$MODULE" "$@"
        else
            echo "Error: Module '$MODULE' not found"
            echo ""
            echo "Available modules:"
            for m in "${MODULES[@]}"; do
                echo "  - $m"
            done
            exit 1
        fi
        ;;
esac
