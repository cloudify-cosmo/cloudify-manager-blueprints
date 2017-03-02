#!/bin/bash -e

if [ $1 == "validate-blueprints" ]; then
  blueprints=`find . -name "*-manager-blueprint.yaml"`
  for blueprint in $blueprints; do
    cfy blueprints validate $blueprint
  done
elif [ $1 == "flake8" ]; then
  flake8 .
else
  exit 1
fi;

