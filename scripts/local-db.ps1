param([ValidateSet('start', 'stop', 'status')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pgCtl = Join-Path $projectRoot '.local/pgsql/bin/pg_ctl.exe'
$pgData = Join-Path $projectRoot '.local/pgdata'
$pgLog = Join-Path $projectRoot '.local/postgres.log'
if ($Action -eq 'start') {
    & $pgCtl -D $pgData -l $pgLog -w start
} elseif ($Action -eq 'stop') {
    & $pgCtl -D $pgData -m fast -w stop
} else {
    & $pgCtl -D $pgData status
}
exit $LASTEXITCODE
