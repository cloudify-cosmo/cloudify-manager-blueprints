#!/bin/bash -e

if [ "${OP}" == "validate-blueprints" ]; then
  cfy init
  blueprints=`find . -name "*-manager-blueprint.yaml"`
  for blueprint in $blueprints; do
    cfy blueprints validate -p $blueprint
  done
elif [ "${OP}" == "flake8" ]; then
  flake8 .
elif [ "${OP}" == "bootstrap-sanity" ]; then
  if [ "${TRAVIS_TAG}" == "bootstrap-sanity" ]; then
    cd tests
    pip install -r bootstrap-sanity-requirements.txt
    python sanity.py
    exit $?
  else
    echo "Not bootstrap-sanity tag, skipping bootstrap sanity test."
  fi;
else
  exit 1
fi;

