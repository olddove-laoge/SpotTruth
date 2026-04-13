param(
  [string]$BaseUrl = "http://127.0.0.1:8080",
  [string]$LoginAccount = "spottruth_user",
  [string]$LoginPassword = "spottruth_user_123",
  [string]$ClassifyProductName = "iPhone 15",
  [int]$HealthRequests = 2000,
  [int]$HealthConcurrency = 80,
  [int]$LoginRequests = 80,
  [int]$LoginConcurrency = 50,
  [int]$ClassifyRequests = 100,
  [int]$ClassifyConcurrency = 50,
  [string]$OutputRoot = "./observability/loadtest_results",
  [string]$ApiKey = "",
  [switch]$DisableBucketAutoFit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-HeyCommand {
  $cmd = Get-Command hey -ErrorAction SilentlyContinue
  if ($null -eq $cmd) {
    throw "未找到 hey 命令。请先安装：go install github.com/rakyll/hey@latest"
  }
  return $cmd.Path
}

function Resolve-PythonCommand {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($null -ne $python) {
    return @($python.Path)
  }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($null -ne $py) {
    return @($py.Path, "-3")
  }
  throw "未找到 python 命令。请安装 Python 3。"
}

function Get-EnvValueFromFile {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string]$Key
  )

  if (-not (Test-Path $FilePath)) {
    return ""
  }

  foreach ($line in Get-Content -Path $FilePath) {
    $trimmed = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
    if ($trimmed.StartsWith("#")) { continue }
    if (-not $trimmed.Contains("=")) { continue }

    $pair = $trimmed.Split("=", 2)
    if ($pair.Length -ne 2) { continue }

    if ($pair[0].Trim() -eq $Key) {
      return $pair[1].Trim()
    }
  }

  return ""
}

function Invoke-HeyScenario {
  param(
    [Parameter(Mandatory = $true)][string]$HeyPath,
    [Parameter(Mandatory = $true)][string]$ScenarioName,
    [Parameter(Mandatory = $true)][string[]]$Args,
    [Parameter(Mandatory = $true)][string]$RunDir
  )

  $rawText = Join-Path $RunDir ("{0}.raw.txt" -f $ScenarioName)
  $rawCsv = Join-Path $RunDir ("{0}.raw.csv" -f $ScenarioName)

  Write-Host ("[loadtest] scenario={0} (summary)" -f $ScenarioName)
  & $HeyPath @Args 2>&1 | Tee-Object -FilePath $rawText | Out-Null

  Write-Host ("[loadtest] scenario={0} (csv)" -f $ScenarioName)
  $csvArgs = @("-o", "csv") + $Args
  & $HeyPath @csvArgs | Out-File -FilePath $rawCsv -Encoding utf8
}

$scriptDir = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $scriptDir
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$apiKeyValue = if ([string]::IsNullOrWhiteSpace($ApiKey)) { "loadtest-$timestamp" } else { $ApiKey }
$loginApiKey = "$apiKeyValue-login"
$classifyApiKey = "$apiKeyValue-classify"

$gatewayEnvPath = Join-Path $projectRoot "gateway.env"
if (-not $DisableBucketAutoFit) {
  $bucketEnabledRaw = Get-EnvValueFromFile -FilePath $gatewayEnvPath -Key "BUCKET_LIMIT_ENABLED"
  $bucketRequestsRaw = Get-EnvValueFromFile -FilePath $gatewayEnvPath -Key "BUCKET_LIMIT_REQUESTS"

  $bucketEnabled = $false
  if (-not [string]::IsNullOrWhiteSpace($bucketEnabledRaw)) {
    $bucketEnabled = $bucketEnabledRaw.ToLowerInvariant() -eq "true"
  }

  $bucketRequests = 0
  if (-not [string]::IsNullOrWhiteSpace($bucketRequestsRaw)) {
    [void][int]::TryParse($bucketRequestsRaw, [ref]$bucketRequests)
  }

  if ($bucketEnabled -and $bucketRequests -gt 0 -and $ClassifyRequests -ge $bucketRequests) {
    $adjusted = [Math]::Max(1, $bucketRequests - 5)
    Write-Warning ("检测到 BUCKET_LIMIT_REQUESTS={0}，为避免 classify 全量 429，自动将 ClassifyRequests 从 {1} 调整为 {2}。可用 -DisableBucketAutoFit 关闭此行为。" -f $bucketRequests, $ClassifyRequests, $adjusted)
    $ClassifyRequests = $adjusted
  }

  if ($bucketEnabled -and $bucketRequests -gt 0 -and $LoginRequests -ge $bucketRequests) {
    $adjusted = [Math]::Max(1, $bucketRequests - 10)
    Write-Warning ("检测到 BUCKET_LIMIT_REQUESTS={0}，为避免 login 场景被桶限流，自动将 LoginRequests 从 {1} 调整为 {2}。可用 -DisableBucketAutoFit 关闭此行为。" -f $bucketRequests, $LoginRequests, $adjusted)
    $LoginRequests = $adjusted
  }
}

$outputRootAbs = if ([System.IO.Path]::IsPathRooted($OutputRoot)) {
  $OutputRoot
} else {
  Join-Path $projectRoot $OutputRoot
}
New-Item -ItemType Directory -Path $outputRootAbs -Force | Out-Null
$runDir = Join-Path $outputRootAbs $timestamp
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$meta = @{
  generated_at = (Get-Date).ToString("o")
  base_url = $BaseUrl
  host = $env:COMPUTERNAME
  api_key = $apiKeyValue
  login_api_key = $loginApiKey
  classify_api_key = $classifyApiKey
  disable_bucket_autofit = [bool]$DisableBucketAutoFit
  scenarios = @{
    healthz = @{ requests = $HealthRequests; concurrency = $HealthConcurrency }
    login = @{ requests = $LoginRequests; concurrency = $LoginConcurrency }
    classify = @{ requests = $ClassifyRequests; concurrency = $ClassifyConcurrency }
  }
}
$meta | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $runDir "run.meta.json") -Encoding utf8

$heyPath = Resolve-HeyCommand

Write-Host "[loadtest] capture metrics before"
try {
  Invoke-RestMethod -Uri "$BaseUrl/metrics/json" -Method GET |
    ConvertTo-Json -Depth 10 |
    Out-File -FilePath (Join-Path $runDir "metrics.before.json") -Encoding utf8
} catch {
  "{}" | Out-File -FilePath (Join-Path $runDir "metrics.before.json") -Encoding utf8
}

$loginPayload = @{ account = $LoginAccount; password = $LoginPassword; login_type = "password" } | ConvertTo-Json -Compress

$healthArgs = @(
  "-n", "$HealthRequests",
  "-c", "$HealthConcurrency",
  "$BaseUrl/healthz"
)
Invoke-HeyScenario -HeyPath $heyPath -ScenarioName "healthz" -Args $healthArgs -RunDir $runDir

$loginArgs = @(
  "-n", "$LoginRequests",
  "-c", "$LoginConcurrency",
  "-m", "POST",
  "-H", "Content-Type: application/json",
  "-H", "X-API-Key: $loginApiKey",
  "-d", $loginPayload,
  "$BaseUrl/api/v1/auth/login"
)
Invoke-HeyScenario -HeyPath $heyPath -ScenarioName "login" -Args $loginArgs -RunDir $runDir

Write-Host "[loadtest] fetch access token"
$token = ""
try {
  $loginResp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $loginPayload
  if ($null -ne $loginResp.data -and $null -ne $loginResp.data.access_token) {
    $token = [string]$loginResp.data.access_token
  }
} catch {
  $token = ""
}

if ([string]::IsNullOrWhiteSpace($token)) {
  Write-Warning "未拿到 access_token，跳过 classify 场景。"
} else {
  $classifyPayload = @{ product_name = $ClassifyProductName } | ConvertTo-Json -Compress
  $classifyArgs = @(
    "-n", "$ClassifyRequests",
    "-c", "$ClassifyConcurrency",
    "-m", "POST",
    "-H", "Content-Type: application/json",
    "-H", "X-API-Key: $classifyApiKey",
    "-H", "Authorization: Bearer $token",
    "-d", $classifyPayload,
    "$BaseUrl/api/classify"
  )
  Invoke-HeyScenario -HeyPath $heyPath -ScenarioName "classify" -Args $classifyArgs -RunDir $runDir
}

Write-Host "[loadtest] capture metrics after"
try {
  Invoke-RestMethod -Uri "$BaseUrl/metrics/json" -Method GET |
    ConvertTo-Json -Depth 10 |
    Out-File -FilePath (Join-Path $runDir "metrics.after.json") -Encoding utf8
} catch {
  "{}" | Out-File -FilePath (Join-Path $runDir "metrics.after.json") -Encoding utf8
}

$pythonCmd = Resolve-PythonCommand
$plotScript = Join-Path $scriptDir "plot_hey_results.py"
$reportScript = Join-Path $scriptDir "generate_loadtest_report_page.py"
$chartDir = Join-Path $runDir "charts"
New-Item -ItemType Directory -Path $chartDir -Force | Out-Null

Write-Host "[loadtest] build charts"
$pythonExe = $pythonCmd[0]
$pythonArgs = @()
if ($pythonCmd.Length -gt 1) {
  $pythonArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}
& $pythonExe @pythonArgs $plotScript --input-dir $runDir --output-dir $chartDir --title-prefix "SpotTruth Gateway"

$summaryJson = Join-Path $chartDir "combined.summary.json"
$reportHtml = Join-Path $runDir "loadtest_report.html"

Write-Host "[loadtest] build one-page report"
& $pythonExe @pythonArgs $reportScript `
  --summary-json $summaryJson `
  --charts-dir $chartDir `
  --metrics-before (Join-Path $runDir "metrics.before.json") `
  --metrics-after (Join-Path $runDir "metrics.after.json") `
  --output-html $reportHtml `
  --title "SpotTruth 网关压测比赛汇报"

Write-Host "[done] 压测完成，结果目录: $runDir"
Write-Host "[done] 原始压测: *.raw.txt + *.raw.csv"
Write-Host "[done] 图表与汇总: charts/*.png + charts/combined.summary.md"
Write-Host "[done] 汇报模板页: loadtest_report.html"
