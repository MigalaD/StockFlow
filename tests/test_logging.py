"""
Testy dla app_logging.py – konfiguracja loggera i odczyt logów.
"""
from app_logging import get_logger, read_recent_logs, get_log_file_path


def test_get_logger_returns_logger():
    log = get_logger("test_module")
    assert log.name.startswith("stockapp")


def test_logger_writes_and_reads():
    log = get_logger("test_write")
    marker = "UNIKALNY_MARKER_TESTOWY_12345"
    log.info(marker)
    # odczyt ostatnich linii powinien zawierać nasz marker
    lines = read_recent_logs(50)
    assert any(marker in ln for ln in lines)


def test_get_log_file_path_is_absolute():
    import os
    path = get_log_file_path()
    assert os.path.isabs(path)
    assert path.endswith("app.log")


def test_logger_prefixes_namespace():
    log = get_logger("scanner")
    assert "stockapp" in log.name
