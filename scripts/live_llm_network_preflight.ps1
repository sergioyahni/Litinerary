param(
  [Parameter(Position = 1)]
  [string]$EnvFile,
  [string]$HostOverride,
  [int]$TimeoutSeconds = 10
)

$ErrorActionPreference = "Stop"

function Is-PlaceholderValue {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
  $trimmed = $Value.Trim()
  return $trimmed.StartsWith("<") -and $trimmed.EndsWith(">")
}

function Set-EnvFromFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }

  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) { return }
    $separatorIndex = $line.IndexOf("=")
    if ($separatorIndex -le 0) { return }

    $name = $line.Substring(0, $separatorIndex).Trim()
    if ($name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") { return }

    $value = $line.Substring($separatorIndex + 1).Trim()
    if (
      ($value.StartsWith('"') -and $value.EndsWith('"')) -or
      ($value.StartsWith("'") -and $value.EndsWith("'"))
    ) {
      $value = $value.Substring(1, $value.Length - 2)
    }

    $existing = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($existing)) {
      [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }

  return $true
}

function Present {
  param([string]$Name)
  return -not (Is-PlaceholderValue ([Environment]::GetEnvironmentVariable($Name)))
}

function Safe-Reason {
  param([string]$Message)
  if ([string]::IsNullOrWhiteSpace($Message)) { return "none" }
  $lower = $Message.ToLowerInvariant()
  if ($lower.Contains("certificate") -or $lower.Contains("tls") -or $lower.Contains("ssl")) { return "tls" }
  if ($lower.Contains("dns") -or $lower.Contains("name") -or $lower.Contains("resolve")) { return "dns" }
  if ($lower.Contains("proxy")) { return "proxy" }
  if ($lower.Contains("timeout") -or $lower.Contains("timed out")) { return "timeout" }
  if ($lower.Contains("refused")) { return "connection_refused" }
  return "unknown"
}

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$developmentEnvPath = Join-Path $repoRoot ".env.development.local"
$localEnvPath = Join-Path $repoRoot ".env.local"
$loadedEnvSource = "<none>"

if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
  if ($EnvFile.Trim().StartsWith("-")) {
    throw "EnvFile must be a path. Did you mean to pass $EnvFile as a named switch?"
  }
  $resolvedEnvFile = Resolve-Path -LiteralPath $EnvFile -ErrorAction Stop
  if (Set-EnvFromFile $resolvedEnvFile.Path) {
    $loadedEnvSource = Split-Path -Leaf $resolvedEnvFile.Path
  }
} elseif (Test-Path -LiteralPath $developmentEnvPath -PathType Leaf) {
  if (Set-EnvFromFile $developmentEnvPath) {
    $loadedEnvSource = ".env.development.local"
  }
} elseif (Test-Path -LiteralPath $localEnvPath -PathType Leaf) {
  if (Set-EnvFromFile $localEnvPath) {
    $loadedEnvSource = ".env.local"
  }
}

$baseUrl = [Environment]::GetEnvironmentVariable("LLM_BASE_URL")
if (Is-PlaceholderValue $baseUrl) { $baseUrl = "https://api.openai.com/v1" }
$uri = [Uri]$baseUrl
$hostName = if ([string]::IsNullOrWhiteSpace($HostOverride)) { $uri.Host } else { $HostOverride }
$scheme = $uri.Scheme
$path = $uri.AbsolutePath.TrimEnd("/")
if ([string]::IsNullOrWhiteSpace($path)) { $path = "/" }

Write-Output "loadedEnvSource=$loadedEnvSource"
Write-Output "endpointScheme=$scheme"
Write-Output "endpointHost=$hostName"
Write-Output "endpointBasePath=$path"
Write-Output "timeoutSeconds=$TimeoutSeconds"
Write-Output ("httpProxyPresent=" + ((Present "HTTP_PROXY") -or (Present "http_proxy")))
Write-Output ("httpsProxyPresent=" + ((Present "HTTPS_PROXY") -or (Present "https_proxy")))
Write-Output ("noProxyPresent=" + ((Present "NO_PROXY") -or (Present "no_proxy")))
Write-Output ("sslCertFilePresent=" + (Present "SSL_CERT_FILE"))
Write-Output ("sslCertDirPresent=" + (Present "SSL_CERT_DIR"))
Write-Output ("requestsCaBundlePresent=" + (Present "REQUESTS_CA_BUNDLE"))

$dnsOk = $false
try {
  Resolve-DnsName -Name $hostName -ErrorAction Stop | Out-Null
  $dnsOk = $true
  Write-Output "dnsOk=True"
} catch {
  Write-Output "dnsOk=False"
  Write-Output ("dnsFailureCategory=" + (Safe-Reason $_.Exception.Message))
}

$tcpOk = $false
try {
  $client = [System.Net.Sockets.TcpClient]::new()
  $connect = $client.BeginConnect($hostName, 443, $null, $null)
  if (-not $connect.AsyncWaitHandle.WaitOne([TimeSpan]::FromSeconds($TimeoutSeconds))) {
    throw "TCP connection timed out."
  }
  $client.EndConnect($connect)
  $tcpOk = $true
  Write-Output "tcp443Ok=True"
} catch {
  Write-Output "tcp443Ok=False"
  Write-Output ("tcpFailureCategory=" + (Safe-Reason $_.Exception.Message))
} finally {
  if ($client) { $client.Close() }
}

$httpsOk = $false
try {
  $request = [System.Net.HttpWebRequest]::Create($baseUrl)
  $request.Method = "GET"
  $request.Timeout = $TimeoutSeconds * 1000
  $request.UserAgent = "LitineraryNetworkPreflight/1.0"
  $response = $request.GetResponse()
  $httpsOk = $true
  Write-Output "httpsOk=True"
  Write-Output ("httpsStatusCode=" + ([int]$response.StatusCode))
  $response.Close()
} catch [System.Net.WebException] {
  if ($_.Exception.Response) {
    $httpsOk = $true
    Write-Output "httpsOk=True"
    Write-Output ("httpsStatusCode=" + ([int]$_.Exception.Response.StatusCode))
    $_.Exception.Response.Close()
  } else {
    Write-Output "httpsOk=False"
    Write-Output ("httpsFailureCategory=" + (Safe-Reason $_.Exception.Message))
  }
} catch {
  Write-Output "httpsOk=False"
  Write-Output ("httpsFailureCategory=" + (Safe-Reason $_.Exception.Message))
}

$pythonCandidates = @(
  @{ Path = (Join-Path $repoRoot "venv\Scripts\python.exe"); Source = "repo_venv" },
  @{ Path = (Join-Path $repoRoot "..\venv\Scripts\python.exe"); Source = "parent_venv" }
)
$python = $null
$pythonSource = "none"
foreach ($candidate in $pythonCandidates) {
  if (Test-Path -LiteralPath $candidate.Path -PathType Leaf) {
    $python = (Resolve-Path -LiteralPath $candidate.Path).Path
    $pythonSource = $candidate.Source
    break
  }
}
Write-Output "backendPythonSource=$pythonSource"
$pythonOk = $false
if ($python) {
  $pythonScript = @'
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

base_url = os.environ.get("LLM_BASE_URL") or "https://api.openai.com/v1"
timeout = float(os.environ.get("LLM_TIMEOUT_SECONDS") or "10")
parsed = urlparse(base_url)

def category(exc):
    text = str(exc).lower()
    if isinstance(exc, socket.gaierror) or "getaddrinfo" in text:
        return "dns"
    if isinstance(exc, ssl.SSLError) or "certificate" in text or "ssl" in text or "tls" in text:
        return "tls"
    if isinstance(exc, TimeoutError) or "timeout" in text or "timed out" in text:
        return "timeout"
    if isinstance(exc, ConnectionRefusedError) or "refused" in text:
        return "connection_refused"
    if "proxy" in text:
        return "proxy"
    return "unknown"

try:
    with urllib.request.urlopen(base_url, timeout=timeout) as response:
        print("backendPythonHttpsOk=True")
        print(f"backendPythonStatusCode={response.status}")
except urllib.error.HTTPError as exc:
    print("backendPythonHttpsOk=True")
    print(f"backendPythonStatusCode={exc.code}")
except urllib.error.URLError as exc:
    print("backendPythonHttpsOk=False")
    print(f"backendPythonFailureCategory={category(exc.reason)}")
except Exception as exc:
    print("backendPythonHttpsOk=False")
    print(f"backendPythonFailureCategory={category(exc)}")
print(f"backendPythonSslDefaultVerifyPathsPresent={bool(ssl.get_default_verify_paths().cafile or ssl.get_default_verify_paths().capath)}")
'@
  $tmpScript = Join-Path $env:TEMP ("litinerary_network_preflight_" + [guid]::NewGuid().ToString("N") + ".py")
  try {
    Set-Content -LiteralPath $tmpScript -Value $pythonScript -Encoding UTF8
    $pythonOutput = & $python $tmpScript
    $pythonOutput | ForEach-Object {
      if ($_ -eq "backendPythonHttpsOk=True") { $pythonOk = $true }
      Write-Output $_
    }
  } finally {
    Remove-Item -LiteralPath $tmpScript -Force -ErrorAction SilentlyContinue
  }
} else {
  Write-Output "backendPythonHttpsOk=False"
  Write-Output "backendPythonFailureCategory=python_not_found"
}

Write-Output ("networkPreflightReady=" + ($dnsOk -and $tcpOk -and $httpsOk -and $pythonOk))
