#!/bin/bash

# Script to manage Docker containers

start() {
  docker compose up -d
}

build() {
  docker compose build
}

test() {
  docker compose run --rm unittest python -m pytest
}

stop() {
  docker compose down
}

usage() {
  echo "Usage: $0 {start|build|test|stop}"
  exit 1
}

# Check the command-line arguments
case "$1" in
  start)
    start
    ;;
  build)
    build
    ;;
  test)
    test
    ;;
  stop)
    stop
    ;;
  *)
    usage
    ;;
esac
