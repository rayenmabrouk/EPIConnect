#!/usr/bin/env bash
# JMESPath literals use backticks inside single-quoted --query strings:
# shellcheck disable=SC2016
# Roll out one image to the ECS service.
#
#   scripts/ecs-deploy.sh <image-uri>
#
# 1. take the latest task definition revision (Terraform owns everything in it
#    except the image) and register a new revision with the new image
# 2. run database migrations as a ONE-OFF task with that revision and stop if
#    they fail (the running version keeps serving traffic)
# 3. point the service at the new revision; ECS starts the new task, waits for
#    the ALB health check, then drains the old one (rolling, zero downtime).
#    The deployment circuit breaker rolls back automatically if the new task
#    never becomes healthy.
#
# Settings are read from SSM Parameter Store (/epiconnect/deploy/*), written by
# Terraform, so nothing environment-specific is hard-coded in the pipeline.
set -euo pipefail

IMAGE="${1:?usage: ecs-deploy.sh <image-uri>}"
PREFIX="${SSM_PREFIX:-/epiconnect/deploy}"

param() { aws ssm get-parameter --name "$PREFIX/$1" --query Parameter.Value --output text; }

CLUSTER=$(param cluster)
SERVICE=$(param service)
FAMILY=$(param task_family)
SUBNETS=$(param subnets)
SECURITY_GROUP=$(param security_group)

echo "::group::Register task definition revision for $IMAGE"
PREVIOUS_TD=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].taskDefinition' --output text)
aws ecs describe-task-definition --task-definition "$FAMILY" --query taskDefinition --output json \
  | jq --arg img "$IMAGE" '
      .containerDefinitions |= map(if .name == "web" then .image = $img else . end)
      | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities,
            .registeredAt, .registeredBy, .deregisteredAt)' > /tmp/taskdef.json
NEW_TD=$(aws ecs register-task-definition --cli-input-json file:///tmp/taskdef.json \
  --query taskDefinition.taskDefinitionArn --output text)
echo "previous: $PREVIOUS_TD"
echo "new:      $NEW_TD"
# Tell the workflow what to roll back to if a later step (smoke test) fails.
# Not on the very first deployment: the previous revision is Terraform's
# placeholder whose image does not exist.
PREVIOUS_DESIRED=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].desiredCount' --output text)
if [ -n "${GITHUB_OUTPUT:-}" ] && [ "$PREVIOUS_DESIRED" -gt 0 ]; then
  echo "previous_task_definition=$PREVIOUS_TD" >> "$GITHUB_OUTPUT"
fi
echo "::endgroup::"

echo "::group::Run migrations (one-off task)"
TASK_ARN=$(aws ecs run-task --cluster "$CLUSTER" --task-definition "$NEW_TD" --launch-type FARGATE \
  --started-by "pipeline-migrate" \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SECURITY_GROUP}],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"web","command":["migrate"]}]}' \
  --query 'tasks[0].taskArn' --output text)
echo "task: $TASK_ARN"
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"
EXIT_CODE=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[?name==`web`].exitCode | [0]' --output text)
if [ "$EXIT_CODE" != "0" ]; then
  REASON=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" --query 'tasks[0].stoppedReason' --output text)
  echo "::error::Migration task failed (exit code: $EXIT_CODE, reason: $REASON). Service NOT updated."
  exit 1
fi
echo "migrations applied"
echo "::endgroup::"

echo "::group::Update service"
DESIRED=$PREVIOUS_DESIRED
[ "$DESIRED" -lt 1 ] && DESIRED=1   # first deployment: Terraform creates the service at 0
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" \
  --task-definition "$NEW_TD" --desired-count "$DESIRED" --query 'service.serviceName' --output text
echo "waiting for the service to become stable..."
if ! aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"; then
  echo "::error::Service did not stabilise with $NEW_TD"
  exit 1
fi
ROLLOUT=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].deployments[?status==`PRIMARY`].rolloutState | [0]' --output text)
RUNNING_TD=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].taskDefinition' --output text)
echo "rollout state: $ROLLOUT, running: $RUNNING_TD"
if [ "$RUNNING_TD" != "$NEW_TD" ]; then
  echo "::error::Circuit breaker rolled the service back to $RUNNING_TD"
  exit 1
fi
echo "::endgroup::"
echo "deployed $NEW_TD"
