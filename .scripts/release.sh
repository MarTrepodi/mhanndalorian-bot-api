#!/usr/bin/env bash

git-changelog -B auto -Tio ../CHANGELOG.md -c angular -s build,deps,fix,feat,refactor -n semver
