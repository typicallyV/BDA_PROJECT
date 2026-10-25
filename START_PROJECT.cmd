@echo off
setlocal
cd /d "%~dp0"
rem Reuse the already provisioned workspace runtime when available.
if exist vendor\gradio\__init__.py (
  if not exist .venv\Scripts\python.exe (echo Workspace Python runtime is missing. Run setup with Python 3 first.& pause & exit /b 1)
  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
  set "PYTHONPATH=%~dp0vendor"
  if exist C:\Java\jdk\bin\java.exe set "JAVA_HOME=C:\Java\jdk"
  if exist C:\hadoop\bin\hadoop.cmd set "HADOOP_HOME=C:\hadoop"
  if exist hadoop_conf\core-site.xml (
    set "HADOOP_CONF_DIR=%~dp0hadoop_conf"
    set "HDFS_URI=hdfs://localhost:9000"
  )
  if not exist output\hadoop_logs mkdir output\hadoop_logs
  set "HADOOP_LOG_DIR=%~dp0output\hadoop_logs"
  goto run_app
)
where py >nul 2>nul
if errorlevel 1 (echo Install Python 3.10-3.12 and add the py launcher to PATH.& pause & exit /b 1)
py -3 -c "import sys; print(sys.version)" >nul 2>nul
if errorlevel 1 (echo Python 3 is required. Python 2.7 cannot run Gradio or PySpark.& pause & exit /b 1)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
%PYTHON_EXE% -m pip install --upgrade pip
%PYTHON_EXE% -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed.& pause & exit /b 1)
if not exist data\kaggle_social\*.csv (
  echo Downloading Kaggle data. Configure Kaggle API credentials if prompted by an error.
  %PYTHON_EXE% download_dataset.py
  if errorlevel 1 (echo Place Twitter_Data.csv and Reddit_Data.csv in data\kaggle_social, then rerun.& pause & exit /b 1)
)
:run_app
%PYTHON_EXE% app.py

