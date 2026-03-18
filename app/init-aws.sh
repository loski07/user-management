#!/bin/bash

# Create S3 bucket
echo "Creating S3 bucket: $S3_BUCKET_NAME"
aws s3 mb s3://"$S3_BUCKET_NAME" --endpoint-url="$AWS_ENDPOINT_URL"

# Create DynamoDB table
echo "Creating DynamoDB table: $DYNAMODB_TABLE_NAME"
aws dynamodb create-table \
    --table-name "$DYNAMODB_TABLE_NAME" \
    --attribute-definitions AttributeName=email,AttributeType=S \
    --key-schema AttributeName=email,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url="$AWS_ENDPOINT_URL"

echo "Localstack resources initialized."
