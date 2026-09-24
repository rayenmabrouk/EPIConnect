# EPIConnect - push the current AWS Academy session credentials to GitHub
# Actions secrets. AWS Academy blocks IAM role / OIDC provider creation, so the
# pipeline uses the lab's short-lived session credentials (they expire when the
# lab session ends). In a normal AWS account this script is replaced by an
# OIDC role (see docs/ARCHITECTURE.md).
#
# Run after pasting the lab's "AWS CLI" credentials into ~/.aws/credentials:
#   powershell -ExecutionPolicy Bypass -File scripts\refresh-github-aws-secrets.ps1
param([string]$Repo = "rayenmabrouk/EPIConnect")

$credFile = Join-Path $HOME ".aws\credentials"
$values = @{}
foreach ($line in Get-Content $credFile) {
    if ($line -match '^\s*(aws_access_key_id|aws_secret_access_key|aws_session_token)\s*=\s*(\S+)\s*$') {
        $values[$Matches[1]] = $Matches[2]
    }
}
foreach ($k in 'aws_access_key_id', 'aws_secret_access_key', 'aws_session_token') {
    if (-not $values.ContainsKey($k)) { throw "$k not found in $credFile" }
}

# Refuse to upload expired credentials
$account = aws sts get-caller-identity --query Account --output text
if ($LASTEXITCODE -ne 0) { throw "Credentials in $credFile are not valid (lab session expired?)" }

$map = @{
    AWS_ACCESS_KEY_ID     = 'aws_access_key_id'
    AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
    AWS_SESSION_TOKEN     = 'aws_session_token'
}
foreach ($secret in $map.Keys) {
    # --body is read from the variable, never echoed to the console
    gh secret set $secret --repo $Repo --body $values[$map[$secret]]
    if ($LASTEXITCODE -ne 0) { throw "Failed to set $secret" }
}
Write-Host "GitHub secrets updated for $Repo (account $account). Valid until the lab session ends."
