@echo off
setlocal
cd /d "%~dp0"
if not exist output\spark_posts\part-*.csv (echo Run the Spark analysis first.& exit /b 1)
where hadoop >nul 2>nul
if errorlevel 1 (echo Hadoop is not in PATH.& exit /b 1)
if exist "%HADOOP_HOME%\hadoop.cmd" for %%I in ("%HADOOP_HOME%\..") do set "HADOOP_HOME=%%~fI"
if not exist "%HADOOP_HOME%\bin\hadoop.cmd" (echo Set HADOOP_HOME to the Hadoop root folder.& exit /b 1)
set "HADOOP_CONF_DIR=%~dp0hadoop_conf"
set "HADOOP_LOG_DIR=%~dp0output\hadoop_logs"
if exist .venv\Scripts\python.exe (set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe") else (echo Run START_PROJECT.cmd first to provision Python.& exit /b 1)
set "STREAMING_JAR="
for %%F in ("%HADOOP_HOME%\share\hadoop\tools\lib\hadoop-streaming-*.jar") do if exist "%%~fF" set "STREAMING_JAR=%%~fF"
if "%STREAMING_JAR%"=="" (echo Hadoop Streaming JAR not found.& exit /b 1)
hadoop fs -mkdir -p /social-media/input
if errorlevel 1 (echo HDFS is not running. Run START_HADOOP.cmd first.& exit /b 1)
for %%F in (output\spark_posts\part-*.csv) do hadoop fs -put -f "%%~fF" /social-media/input/
hadoop fs -rm -r -f /social-media/output >nul 2>nul
hadoop jar "%STREAMING_JAR%" -file "%~dp0mapper.py" -file "%~dp0reducer.py" -mapper "%PYTHON_EXE% mapper.py" -reducer "%PYTHON_EXE% reducer.py" -input /social-media/input -output /social-media/output
if errorlevel 1 (echo Hadoop Streaming job failed. Check Hadoop logs.& exit /b 1)
echo ===== POST COUNTS BY PLATFORM =====
hadoop fs -cat /social-media/output/part-*
