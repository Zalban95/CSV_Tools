@echo off
rem Launch the CSV Tools GUI.
rem Uses pythonw so no console window stays open.
pushd "%~dp0"
start "" pythonw csv_tool.py
popd
