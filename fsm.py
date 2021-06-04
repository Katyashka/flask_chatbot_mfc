from enum import Enum


class States(Enum):
    # S_EDIT = "0"  # Начало редактирования данных о пользователе
    S_ENTER_SURNAME = "1"
    S_ENTER_NAME = "2"
    S_ENTER_PATRONYMIC = "3"
    # S_CHOOSE_ROLE = "4"
    # S_APPROVED = "5"