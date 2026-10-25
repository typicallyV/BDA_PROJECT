$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
if (-not $env:HADOOP_HOME -or -not (Test-Path (Join-Path $env:HADOOP_HOME "bin\hdfs.cmd"))) { $env:HADOOP_HOME = "C:\hadoop" }
if (-not $env:JAVA_HOME -or -not (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) { $env:JAVA_HOME = "C:\Java\jdk" }
if (-not (Test-Path (Join-Path $env:HADOOP_HOME "bin\hdfs.cmd"))) { throw "Set HADOOP_HOME to the Hadoop installation root." }
if (-not (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) { throw "Set JAVA_HOME to a Java 8, 11, or 17 installation." }
$env:HADOOP_CONF_DIR = Join-Path $root "hadoop_conf"
$env:HADOOP_LOG_DIR = Join-Path $root "output\hadoop_logs"
New-Item -ItemType Directory -Force -Path $env:HADOOP_CONF_DIR | Out-Null
$rootUri = ([Uri]$root).AbsoluteUri.TrimEnd('/')
$coreConfig = @"
<?xml version="1.0"?>
<configuration>
  <property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
</configuration>
"@
$hdfsConfig = @"
<?xml version="1.0"?>
<configuration>
  <property><name>dfs.replication</name><value>1</value></property>
  <property><name>dfs.namenode.name.dir</name><value>$rootUri/hadoop_data/namenode</value></property>
  <property><name>dfs.datanode.data.dir</name><value>$rootUri/hadoop_data/datanode</value></property>
  <property><name>dfs.namenode.datanode.registration.ip-hostname-check</name><value>false</value></property>
</configuration>
"@
Set-Content -Path (Join-Path $env:HADOOP_CONF_DIR "core-site.xml") -Value $coreConfig -Encoding ascii
Set-Content -Path (Join-Path $env:HADOOP_CONF_DIR "hdfs-site.xml") -Value $hdfsConfig -Encoding ascii
$env:PATH = "$($env:JAVA_HOME)\bin;$($env:HADOOP_HOME)\bin;$($env:PATH)"
New-Item -ItemType Directory -Force -Path $env:HADOOP_LOG_DIR, (Join-Path $root "hadoop_data\namenode"), (Join-Path $root "hadoop_data\datanode") | Out-Null
$versionFile = Join-Path $root "hadoop_data\namenode\current\VERSION"
if (-not (Test-Path $versionFile)) {
    $contents = @(Get-ChildItem (Join-Path $root "hadoop_data\namenode") -Force -ErrorAction SilentlyContinue)
    if ($contents.Count -gt 0) { throw "NameNode data exists without a VERSION file. Inspect hadoop_data before formatting." }
    & (Join-Path $env:HADOOP_HOME "bin\hdfs.cmd") namenode -format -nonInteractive
    if ($LASTEXITCODE -ne 0) { throw "NameNode format failed." }
}
$report = @()
$namenodeReady = $false
for ($i = 0; $i -lt 12; $i++) {
    $report = & (Join-Path $env:HADOOP_HOME "bin\hdfs.cmd") dfsadmin -report 2>$null
    if ($LASTEXITCODE -eq 0) { $namenodeReady = $true; break }
    if ($i -eq 0) {
        Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', "call `"$env:HADOOP_HOME\bin\hdfs.cmd`" namenode") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $env:HADOOP_LOG_DIR "namenode-out.log") -RedirectStandardError (Join-Path $env:HADOOP_LOG_DIR "namenode-err.log") | Out-Null
    }
    Start-Sleep -Seconds 5
}
if (-not $namenodeReady) { throw "NameNode did not become ready. See output\hadoop_logs." }
if (($report -join "`n") -notmatch "Live datanodes \(1\)") {
    Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', "call `"$env:HADOOP_HOME\bin\hdfs.cmd`" datanode") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $env:HADOOP_LOG_DIR "datanode-out.log") -RedirectStandardError (Join-Path $env:HADOOP_LOG_DIR "datanode-err.log") | Out-Null
}
$ready = $false
for ($i = 0; $i -lt 24; $i++) {
    $report = & (Join-Path $env:HADOOP_HOME "bin\hdfs.cmd") dfsadmin -report 2>$null
    if ($LASTEXITCODE -eq 0 -and ($report -join "`n") -match "Live datanodes \(1\)") { $ready = $true; break }
    Start-Sleep -Seconds 5
}
if (-not $ready) { throw "HDFS did not become ready. See output\hadoop_logs." }
Write-Output "HDFS is ready at hdfs://localhost:9000."



