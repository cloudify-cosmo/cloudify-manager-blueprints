cfy init
blueprints=`find . -name "*-manager-blueprint.yaml"`
for blueprint in $blueprints; do
    cfy blueprints validate -p $blueprint
done
