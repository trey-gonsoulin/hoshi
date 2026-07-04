#!/usr/bin/env bash
# Deploy the hoshi-ui static build to S3 and invalidate CloudFront.
#
# Prerequisites: aws CLI configured, sam deploy already run at least once.
#
# Usage: ./deploy-ui.sh [--stack STACK_NAME] [--profile AWS_PROFILE]
#
# AWS profile resolution order:
#   1. --profile flag
#   2. AWS_PROFILE env var
#   3. AWS default profile

set -euo pipefail

STACK="hoshi-api"
PROFILE="${AWS_PROFILE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack)    STACK="$2";   shift 2 ;;
    --profile)  PROFILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

AWS_ARGS=()
if [[ -n "$PROFILE" ]]; then
  AWS_ARGS=(--profile "$PROFILE")
  echo "==> Using AWS profile '$PROFILE'"
fi

echo "==> Fetching stack outputs for '$STACK'..."
BUCKET=$(aws "${AWS_ARGS[@]}" cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='UiBucketName'].OutputValue" \
  --output text)

DISTRIBUTION=$(aws "${AWS_ARGS[@]}" cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='UiDistributionId'].OutputValue" \
  --output text)

UI_URL=$(aws "${AWS_ARGS[@]}" cloudformation describe-stacks \
  --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='UiUrl'].OutputValue" \
  --output text)

echo "    Bucket:       $BUCKET"
echo "    Distribution: $DISTRIBUTION"
echo "    URL:          $UI_URL"

echo "==> Building UI..."
cd packages/hoshi-ui
npm run build
cd ../..

echo "==> Syncing to s3://$BUCKET ..."
aws "${AWS_ARGS[@]}" s3 sync packages/hoshi-ui/dist/ "s3://$BUCKET" \
  --delete \
  --cache-control "public,max-age=31536000,immutable" \
  --exclude "index.html"

# index.html must not be cached — browsers always fetch it fresh
aws "${AWS_ARGS[@]}" s3 cp packages/hoshi-ui/dist/index.html "s3://$BUCKET/index.html" \
  --cache-control "no-cache,no-store,must-revalidate"

echo "==> Invalidating CloudFront cache..."
aws "${AWS_ARGS[@]}" cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION" \
  --paths "/*" \
  --query "Invalidation.Id" \
  --output text

echo ""
echo "Done. UI is live at $UI_URL"
