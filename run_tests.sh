# Should I make all these paths relative to the file?
docker build -t netcheck-api-test-runner -f test/Dockerfile .
if [ $? -eq 0 ]; then
    printf "\Running Docker image\n\n"
    docker run --rm --name netcheck-api-test-runner netcheck-api-test-runner
else
    echo "Docker build failed. Exiting."
    exit 1
fi