@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (echo Install Docker Desktop first.& pause & exit /b 1)
docker info >nul 2>nul
if errorlevel 1 (echo Start Docker Desktop first.& pause & exit /b 1)
docker inspect social-media-cassandra >nul 2>nul
if errorlevel 1 (docker run --name social-media-cassandra -p 9042:9042 -d cassandra:5.0) else (docker start social-media-cassandra)
echo Waiting for Cassandra to start...
set /a attempts=0
:wait
set /a attempts+=1
docker exec social-media-cassandra cqlsh -e "DESCRIBE KEYSPACES" >nul 2>nul
if not errorlevel 1 goto ready
if %attempts% GEQ 30 (echo Cassandra is still starting. Run this script again shortly.& pause & exit /b 1)
timeout /t 10 /nobreak >nul
goto wait
:ready
docker exec -i social-media-cassandra cqlsh < schema.cql
if errorlevel 1 (echo Schema setup failed.& pause & exit /b 1)
echo Cassandra ready at localhost:9042.
pause
