param(
  [Parameter(Mandatory=$true)][string]$Raw,   # folder out\wpscan\raw
  [Parameter(Mandatory=$true)][string]$Out    # folder out\wpscan
)

$ErrorActionPreference = "SilentlyContinue"
if (!(Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$kw = 'upload|file.?upload|takeover|account.?takeover|remote.?code.?execution|RCE'
$now = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')

$flat = New-Object System.Collections.Generic.List[object]

Get-ChildItem -LiteralPath $Raw -Filter *.json -File | ForEach-Object {
  try { $j = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json } catch { return }
  $url = $j.target_url
  if (-not $url) { $url = $j.target || $j.scan_aborted_cli_args.url }

  # Core vulns (kadang ada di $j.version.vulnerabilities)
  if ($j.version -and $j.version.vulnerabilities) {
    foreach ($v in $j.version.vulnerabilities) {
      $score = 0
      if ($v.cvss) { [double]::TryParse($v.cvss.ToString(), [ref]$score) | Out-Null }
      elseif ($v.cvssv3 -match '(\d+(\.\d+)?)') { $score = [double]$Matches[1] }
      $sev = if($score -ge 9){'critical'} elseif($score -ge 7){'high'} elseif($score -ge 4){'medium'} else {'low'}
      $title = $v.title
      if (($sev -in @('critical','high')) -and ($title -match $kw)) {
        $cve = ($v.references.cve | Select-Object -First 1) -join ','
        $flat.Add([pscustomobject]@{
          url=$url; cms='wordpress'; type='core'; name='wordpress-core';
          version=$j.version.number; vuln_title=$title; cvss=$score; severity=$sev;
          cve=$cve; ref=((($v.references.url|Select-Object -First 1) -join ',')); ts=$now
        })
      }
    }
  }

  # Plugin vulns
  if ($j.plugins) {
    foreach ($k in $j.plugins.PSObject.Properties.Name) {
      $p = $j.plugins.$k
      $ver = $p.version.number
      foreach ($v in ($p.vulnerabilities|Where-Object {$_})) {
        $score = 0
        if ($v.cvss) { [double]::TryParse($v.cvss.ToString(), [ref]$score) | Out-Null }
        elseif ($v.cvssv3 -match '(\d+(\.\d+)?)') { $score = [double]$Matches[1] }
        $sev = if($score -ge 9){'critical'} elseif($score -ge 7){'high'} elseif($score -ge 4){'medium'} else {'low'}
        $title = $v.title
        if (($sev -in @('critical','high')) -and ($title -match $kw)) {
          $cve = ($v.references.cve | Select-Object -First 1) -join ','
          $flat.Add([pscustomobject]@{
            url=$url; cms='wordpress'; type='plugin'; name=$k;
            version=$ver; vuln_title=$title; cvss=$score; severity=$sev;
            cve=$cve; ref=((($v.references.url|Select-Object -First 1) -join ',')); ts=$now
          })
        }
      }
    }
  }

  # Theme vulns
  if ($j.theme) {
    $t = $j.theme
    $tname = $t.name
    $tver  = $t.version.number
    foreach ($v in ($t.vulnerabilities|Where-Object {$_})) {
      $score = 0
      if ($v.cvss) { [double]::TryParse($v.cvss.ToString(), [ref]$score) | Out-Null }
      elseif ($v.cvssv3 -match '(\d+(\.\d+)?)') { $score = [double]$Matches[1] }
      $sev = if($score -ge 9){'critical'} elseif($score -ge 7){'high'} elseif($score -ge 4){'medium'} else {'low'}
      $title = $v.title
      if (($sev -in @('critical','high')) -and ($title -match $kw)) {
        $cve = ($v.references.cve | Select-Object -First 1) -join ','
        $flat.Add([pscustomobject]@{
          url=$url; cms='wordpress'; type='theme'; name=$tname;
          version=$tver; vuln_title=$title; cvss=$score; severity=$sev;
          cve=$cve; ref=((($v.references.url|Select-Object -First 1) -join ',')); ts=$now
        })
      }
    }
  }
}

# Tulis JSONL + TXT ringkas + summary
$findingsJsonl = Join-Path $Out "findings.jsonl"
$findingsTxt   = Join-Path $Out "findings.txt"
$summaryTxt    = Join-Path $Out "summary.txt"

Remove-Item -Force -ErrorAction SilentlyContinue $findingsJsonl,$findingsTxt,$summaryTxt

$flat | ForEach-Object { ($_ | ConvertTo-Json -Compress) } | Out-File -Encoding ASCII -FilePath $findingsJsonl
$flat | ForEach-Object { "{0} | {1}:{2} | {3} | {4}" -f $_.severity, $_.type, $_.name, $_.vuln_title, $_.url } |
  Out-File -Encoding ASCII -FilePath $findingsTxt

$crit = ($flat | Where-Object {$_.severity -eq 'critical'}).Count
$high = ($flat | Where-Object {$_.severity -eq 'high'}).Count

$lines = @()
$lines += "=== WPScan Summary (upload/takeover/RCE only, High/Critical) ==="
$lines += "Raw Dir : $Raw"
$lines += "Total   : $($flat.Count)"
$lines += "critical: $crit"
$lines += "high    : $high"
$lines += ""
$lines += "Top 30:"
$flat | Sort-Object severity -Descending, cvss -Descending | Select-Object -First 30 |
  ForEach-Object { $lines += ("{0} | {1}:{2} | CVSS {3} | {4}" -f $_.severity, $_.type, $_.name, $_.cvss, $_.url) }
$lines | Out-File -Encoding ASCII -FilePath $summaryTxt

Write-Host "[=] Merge OK -> $Out"
