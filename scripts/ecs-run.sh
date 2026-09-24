#!/usr/bin/env bash
# Run a one-off management command in a Fargate task using the service's
# current task definition (same image, env, secrets and network as the app).
#   scripts/ecs-run.sh seed_perks
#   scripts/ecs-run.sh bootstrap_admin
# Prints the task's log output and exits with the container's exit code.
# JMESPath literals use backticks inside single-quoted --query strings:
# shellcheck disable=SC2016
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: ecs-run.sh <manage.py command> [args...]" >&2; exit 2; }
PREFIX="${SSM_PREFIX:-/epiconnect/deploy}"
param() { aws ssm get-parameter --name "$PREFIX/$1" --query Parameter.Value --output text; }

CLUSTER=$(param cluster)
SERVICE=$(param service)
SUBNETS=$(param subnets)
SECURITY_GROUP=$(param security_group)
TASK_DEF=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --query 'services[0].taskDefinition' --output text)

OVERRIDES=$(printf '%s\0' "$@" | jq -cRs '{containerOverrides: [{name: "web", command: (split("\u0000")[:-1])}]}')
TASK_ARN=$(aws ecs run-task --cluster "$CLUSTER" --task-definition "$TASK_DEF" --launch-type FARGATE \
  --started-by "ops-$1" \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SECURITY_GROUP}],assignPublicIp=ENABLED}" \
  --overrides "$OVERRIDES" --query 'tasks[0].taskArn' --output text)
echo "task: $TASK_ARN ($*)"
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"

TASK_ID="${TASK_ARN##*/}"
LOG_GROUP=$(aws ecs describe-task-definition --task-definition "$TASK_DEF" \
  --query 'taskDefinition.containerDefinitions[0].logConfiguration.options."awslogs-group"' --output text)
aws logs get-log-events --log-group-name "$LOG_GROUP" --log-stream-name "web/web/${TASK_ID}" \
  --query 'events[].message' --output text 2>/dev/null | tr '\t' '\n' || true

EXIT_CODE=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[?name==`web`].exitCode | [0]' --output text)
echo "exit code: $EXIT_CODE"
[ "$EXIT_CODE" = "0" ]
