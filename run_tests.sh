#!/bin/bash

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "Please install and use Act to run CI tests locally. Visit https://github.com/nektos/act for installation instructions."
    exit 1
fi

# Check if '--use-container' is passed as an argument. If so, use github workflow
USE_CONTAINER=false
for arg in "$@"; do
    if [[ "$arg" == "--use-container" ]]; then
        USE_CONTAINER=true
        break
    fi
done

# Run with act if --use-container is true, otherwise use pytest
if [ "$USE_CONTAINER" = true ]; then
    echo "Running tests with act..."
    act
else
    echo "Running tests with pytest..."
    pytest
fi

# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# docker build -t netcheck-api-test-runner -f "$SCRIPT_DIR/test/Dockerfile" "$SCRIPT_DIR"
# if [ $? -eq 0 ]; then
#     echo "Running Docker image"
#     docker run --rm --name netcheck-api-test-runner netcheck-api-test-runner
# else
#     echo "Docker build failed. Exiting."
#     exit 1
# fi