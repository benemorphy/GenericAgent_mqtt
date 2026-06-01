.PHONY: install test lint clean cache clear help

help:
	@echo "GenericAgent - 项目管理命令"
	@echo "  make install   安装项目依赖 (pip install -e .)"
	@echo "  make test      运行测试 (pytest)"
	@echo "  make lint      运行代码检查 (ruff)"
	@echo "  make clean     清理临时文件"
	@echo "  make cache     清理 Python 缓存"
	@echo "  make clear     清理所有生成文件"

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --tb=short -W ignore::DeprecationWarning

lint:
	python -m ruff check . --select=E9,F

lint-all:
	python -m ruff check .

clean:
	if exist __pycache__ rmdir /s /q __pycache__
	if exist .pytest_cache rmdir /s /q .pytest_cache
	if exist build rmdir /s /q build
	if exist dist rmdir /s /q dist
	if exist *.egg-info rmdir /s /q *.egg-info

cache:
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	del /s /q *.pyc 2>nul

clear: clean cache
