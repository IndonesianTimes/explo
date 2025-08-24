# Recon & Vulnerability Scanning (Windows)

## Struktur
- recon_wp_cmd.bat            # runner utama (httpx -> WP detect -> nuclei fallback)
- wp_scan_cmd.bat             # WPScan paralel + merge
- scripts/cms-sort.ps1        # kelompokkan hasil httpx per-CMS
- scripts/wpscan-merge.ps1    # merge & filter High/Critical (upload/takeover/RCE)
- nuclei-config-*.yaml        # config nuclei
- subs.txt                    # contoh input

## Tools (letakkan manual, tidak dikomit)
tools/httpx.exe, tools/nuclei.exe, tools/wpscan.bat (atau ruby -S wpscan),
tools/nuclei-templates/

## Quickstart
cms_sort.bat
recon_wp_cmd.bat
wp_scan_cmd.bat
