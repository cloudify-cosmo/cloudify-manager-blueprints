#!/bin/bash -e

curl --fail --request POST --data @components/provider_context http://localhost/provider/context --header "Content-Type:application/json"