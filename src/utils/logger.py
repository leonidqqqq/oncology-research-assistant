"""Центральная настройка логирования.

Использование:
    from src.utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Что-то произошло")
    log.warning("Предупреждение")
    log.error("Ошибка")
"""
import logging
import sys


def get_logger(name: str = "hakatonleo3") -> logging.Logger:
    """Возвращает настроенный логгер.
    
    Format: 2026-06-28 15:30:21 INFO  [src.agents.verifier] Сообщение
    
    Конфигурируется один раз; повторные вызовы возвращают тот же логгер.
    """
    logger = logging.getLogger(name)
    
    # Защита от повторной инициализации
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False  # не дублировать в root
    
    return logger
