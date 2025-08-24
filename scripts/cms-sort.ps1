param(
  [Parameter(Mandatory=$true)][string]$In,   # httpx JSONL
  [Parameter(Mandatory=$true)][string]$Out   # folder output
)

$ErrorActionPreference = "SilentlyContinue"
if (!(Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

# Peta CMS → kata kunci (pakai lower-case; mudah ditambah)
$cmsMap = @(
  @{name='wordpress';  keys=@('wordpress','wpengine','woocommerce')},
  @{name='joomla';     keys=@('joomla')},
  @{name='drupal';     keys=@('drupal')},
  @{name='magento';    keys=@('magento')},
  @{name='prestashop'; keys=@('prestashop')},
  @{name='opencart';   keys=@('opencart')},
  @{name='shopify';    keys=@('shopify')},
  @{name='ghost';      keys=@('ghost')},
  @{name='wix';        keys=@('wix')},
  @{name='squarespace';keys=@('squarespace')},
  @{name='blogger';    keys=@('blogger','blogspot')},
  @{name='typo3';      keys=@('typo3')},
  @{name='bitrix';     keys=@('bitrix')},
  @{name='umbraco';    keys=@('umbraco')}
)

function Detect-CMS($techLower, $titleLower) {
  foreach ($m in $cmsMap) {
    foreach ($k in $m.keys) {
      if ($techLower.Contains($k) -or $titleLower.Contains($k)) { return $m.name }
    }
  }
  return 'unknown'
}

$rows = New-Object System.Collections.Generic.List[object]

Get-Content -LiteralPath $In | ForEach-Object {
  try { $o = $_ | ConvertFrom-Json } catch { return }
  $url   = $o.url
  $host  = $o.host
  $code  = $o.status_code
  $title = ($o.title | Out-String).Trim()

  $techs = @()
  if ($o.tech) {
    if ($o.tech -is [System.Collections.IEnumerable]) { $techs += ($o.tech | ForEach-Object { $_.ToString() }) }
    else { $techs += $o.tech.ToString() }
  }
  $techLower  = ($techs -join ',').ToLower()
  $titleLower = ($title | Out-String).ToLower()

  $cms = Detect-CMS $techLower $titleLower
  $rows.Add([pscustomobject]@{
    url    = $url
    host   = $host
    status = $code
    title  = $title
    cms    = $cms
    tech   = ($techs -join '; ')
  })
}

# Tulis master CSV
$master = Join-Path $Out "master.csv"
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $master

# Tulis per-CMS (CSV + TXT URL)
$by = $rows | Group-Object cms
foreach ($g in $by) {
  $name = $g.Name
  $csv  = Join-Path $Out ("{0}.csv" -f $name)
  $txt  = Join-Path $Out ("{0}.txt" -f $name)
  $g.Group | Sort-Object host | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $csv
  $g.Group | ForEach-Object { $_.url } | Sort-Object -Unique | Out-File -Encoding ASCII -FilePath $txt
}

# Ringkasan
$sum = Join-Path $Out "summary.txt"
$lines = @()
$lines += "=== CMS Summary ==="
$lines += "Input: $In"
$lines += "Total URLs: " + $rows.Count
$lines += ""
$lines += "Counts per CMS:"
$by | Sort-Object Count -Descending | ForEach-Object { $lines += ("{0,10} : {1}" -f $_.Name, $_.Count) }
$lines | Out-File -Encoding ASCII -FilePath $sum

Write-Host "[=] Done. Output dir: $Out"
