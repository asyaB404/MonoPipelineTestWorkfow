@echo off
set DOCX_PATH=%1
set FEATURE_ID=%2

if "%DOCX_PATH%"=="" (
    echo 用法: run_docx_preprocess.bat 文档路径.docx feature-id
    exit /b 1
)

if "%FEATURE_ID%"=="" (
    echo 用法: run_docx_preprocess.bat 文档路径.docx feature-id
    exit /b 1
)

python Tools/AI/docx_preprocess.py --docx "%DOCX_PATH%" --out "Doc/AI中间产物/%FEATURE_ID%"
if errorlevel 1 exit /b 1

python Tools/AI/testcase_evidence_utils.py --input-dir "Doc/AI中间产物/%FEATURE_ID%"
if errorlevel 1 exit /b 1

echo.
echo 预处理完成：
echo Doc/AI中间产物/%FEATURE_ID%/requirement_text.md
echo Doc/AI中间产物/%FEATURE_ID%/requirement_blocks.json
echo Doc/AI中间产物/%FEATURE_ID%/image_cards.json
echo Doc/AI中间产物/%FEATURE_ID%/image_index.json
echo Doc/AI中间产物/%FEATURE_ID%/evidence_registry.json
echo Doc/AI中间产物/%FEATURE_ID%/evidence_alias_registry.json
echo Doc/AI中间产物/%FEATURE_ID%/evidence_index.md
echo Doc/AI中间产物/%FEATURE_ID%/preprocess_summary.json
