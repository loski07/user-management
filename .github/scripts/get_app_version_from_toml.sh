#!/bin/bash

# SUMMARY:
#   Determines the application version for the CI/CD pipeline by prioritizing manual overrides before falling back to
#   the project metadata.
#
# INPUTS (Environment Variables):
#   VERSION_OVERRIDE : String (Optional). A manually provided version string from the workflow dispatch input.
#   PROJECT_PATH     : String (Required). The relative path from the repository root to the directory containing
#                      'pyproject.toml'.
#
# OUTPUTS (GitHub Actions):
#   version          : String. Written to $GITHUB_OUTPUT. This is the finalized version string used for Docker tagging.
#
# DEPENDENCIES:
#   - grep, cut (Standard Linux utilities)
#   - A valid pyproject.toml file at the provided PROJECT_PATH

if [ -n "$VERSION_OVERRIDE" ]; then
  # Use manual override if provided
  FINAL_VERSION="$VERSION_OVERRIDE"
else
  FINAL_VERSION=$(grep -m 1 'version =' "$PROJECT_PATH/pyproject.toml" | cut -d '"' -f 2)
fi

echo "version=${FINAL_VERSION}" >> $GITHUB_OUTPUT
