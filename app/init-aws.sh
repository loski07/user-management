#!/bin/bash
awslocal s3 mb s3://user-avatars

awslocal dynamodb create-table \
    --table-name users-table \
    --attribute-definitions AttributeName=email,AttributeType=S) \
    --key-schema AttributeName=email,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
