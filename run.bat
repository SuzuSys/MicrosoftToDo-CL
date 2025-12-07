@echo off
cd /d %~dp0

echo ==========================================
echo  Running main.py inside pipenv
echo ==========================================
echo.

REM まず pipenv コマンドがあるか確認
where pipenv >nul 2>&1

if %errorlevel% neq 0 (
    echo pipenv コマンドが見つかりません。
    echo 代わりに "py -m pipenv" で実行してみます...
    echo.

    REM py は exe なので call は不要
    py -m pipenv run python main.py
) else (
    echo pipenv が見つかりました。pipenv run で実行します...
    echo.

    REM pipenv が .bat / .cmd の可能性があるので call が必須
    call pipenv run python main.py
)

echo.
echo --------- Finished (exit code: %errorlevel%) ---------
echo.
pause
