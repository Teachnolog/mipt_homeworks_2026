#!/usr/bin/env python

from collections import defaultdict
from typing import Any

DAY_MIN = 1
DATE_PARTS = 3
MONTH_MIN = 1
MONTH_MAX = 12
FEBRUARY = 2
DAYS_IN_MONTH = {4: 30, 6: 30, 9: 30, 11: 30}

KEY_AMOUNT = "amount"
KEY_DATE = "date"
KEY_CATEGORY = "category"

INCOME_ARGS = 3
COST_ARGS = 4
COST_CATEGORIES_ARGS = 2
STATS_ARGS = 2
CATEGORY_SPLIT_PARTS = 2
CATEGORY_SEPARATOR = "::"

KEY_STATS_CATEGORIES = "categories"

UNKNOWN_COMMAND_MSG = "Unknown command!"
NONPOSITIVE_VALUE_MSG = "Value must be grater than zero!"
INCORRECT_DATE_MSG = "Invalid date!"
NOT_EXISTS_CATEGORY = "Category not exists!"
OP_SUCCESS_MSG = "Added"


EXPENSE_CATEGORIES = {
    "Food": ("Supermarket", "Restaurants", "FastFood", "Coffee", "Delivery"),
    "Transport": ("Taxi", "Public transport", "Gas", "Car service"),
    "Housing": ("Rent", "Utilities", "Repairs", "Furniture"),
    "Health": ("Pharmacy", "Doctors", "Dentist", "Lab tests"),
    "Entertainment": ("Movies", "Concerts", "Games", "Subscriptions"),
    "Clothing": ("Outerwear", "Casual", "Shoes", "Accessories"),
    "Education": ("Courses", "Books", "Tutors"),
    "Communications": ("Mobile", "Internet", "Subscriptions"),
    "Other": ("SomeCategory", "SomeOtherCategory"),
}


financial_transactions_storage: list[dict[str, Any]] = []


def is_leap_year(year: int) -> bool:
    """
    Для заданного года определяет: високосный (True) или невисокосный (False).

    :param int year: Проверяемый год
    :return: Значение високосности.
    :rtype: bool
    """
    if year % 4 != 0:
        return False
    if year % 100 == 0:
        return year % 400 == 0
    return True


def days_in_month(month: int, year: int) -> int:
    days = DAYS_IN_MONTH.get(month)
    if days is not None:
        return days
    if month == FEBRUARY:
        return 29 if is_leap_year(year) else 28
    return 31


def parse_int(s: str) -> int | None:
    if not s:
        return None
    if s[0] in "+-":
        if len(s) == 1:
            return None
        if not s[1:].isdigit():
            return None
    elif not s.isdigit():
        return None
    return int(s)


def extract_date(maybe_dt: str) -> tuple[int, int, int] | None:
    """
    Парсит дату формата DD-MM-YYYY из строки.

    :param str maybe_dt: Проверяемая строка
    :return: tuple формата (день, месяц, год) или None, если дата неправильная.
    :rtype: tuple[int, int, int] | None
    """
    parts = maybe_dt.split("-")
    if len(parts) != DATE_PARTS:
        return None

    day = parse_int(parts[0])
    month = parse_int(parts[1])
    year = parse_int(parts[2])

    if day is None or month is None or year is None:
        return None

    if not (MONTH_MIN <= month <= MONTH_MAX):
        return None
    if not (1 <= day <= days_in_month(month, year)):
        return None
    return day, month, year


def income_handler(amount: float, income_date: str) -> str:
    if amount <= 0:
        financial_transactions_storage.append({})
        return NONPOSITIVE_VALUE_MSG
    date_tuple = extract_date(income_date)
    if date_tuple is None:
        financial_transactions_storage.append({})
        return INCORRECT_DATE_MSG
    financial_transactions_storage.append({KEY_AMOUNT: amount, KEY_DATE: date_tuple})
    return OP_SUCCESS_MSG


def validate_category(category_name: str) -> bool:
    if CATEGORY_SEPARATOR not in category_name:
        return False
    parts = category_name.split(CATEGORY_SEPARATOR)
    if len(parts) != CATEGORY_SPLIT_PARTS:
        return False
    common, target = parts
    return common in EXPENSE_CATEGORIES and target in EXPENSE_CATEGORIES[common]


def cost_handler(category_name: str, amount: float, cost_date: str) -> str:
    if amount <= 0:
        financial_transactions_storage.append({})
        return NONPOSITIVE_VALUE_MSG
    date_tuple = extract_date(cost_date)
    if date_tuple is None:
        financial_transactions_storage.append({})
        return INCORRECT_DATE_MSG
    if not validate_category(category_name):
        financial_transactions_storage.append({})
        return NOT_EXISTS_CATEGORY
    financial_transactions_storage.append(
        {KEY_CATEGORY: category_name, KEY_AMOUNT: amount, KEY_DATE: date_tuple}
    )
    return OP_SUCCESS_MSG


def cost_categories_handler() -> str:
    lines: list[str] = []
    for common, targets in EXPENSE_CATEGORIES.items():
        lines.extend(f"{common}::{target}" for target in targets)
    return "\n".join(lines)


def normalize_date(date_value: Any) -> tuple[int, int, int] | None:
    if isinstance(date_value, tuple) and len(date_value) == DATE_PARTS:
        day, month, year = date_value
        if all(isinstance(x, int) for x in (day, month, year)):
            if MONTH_MIN <= month <= MONTH_MAX and DAY_MIN <= day <= days_in_month(month, year):
                return (day, month, year)
            return None
    if isinstance(date_value, str):
        return extract_date(date_value)
    return None


def filter_transactions_up_to(date: tuple[int, int, int]) -> list[dict[str, Any]]:
    day, month, year = date
    cutoff_key = (year, month, day)
    result = []
    for t in financial_transactions_storage:
        if KEY_DATE not in t:
            continue
        norm = normalize_date(t[KEY_DATE])
        if norm is None:
            continue
        if (norm[2], norm[1], norm[0]) <= cutoff_key:
            result.append(t)
    return result


def is_in_month(transaction: dict[str, Any], target_year: int, target_month: int) -> bool:
    norm = normalize_date(transaction.get(KEY_DATE))
    if norm is None:
        return False
    _, month, year = norm
    return year == target_year and month == target_month


def month_income(transactions: list[dict[str, Any]], year: int, month: int) -> float:
    return float(sum(
        t[KEY_AMOUNT] for t in transactions
        if KEY_CATEGORY not in t and is_in_month(t, year, month)
    ))


def month_expenses(transactions: list[dict[str, Any]], year: int, month: int) -> float:
    return float(sum(
        t[KEY_AMOUNT] for t in transactions
        if KEY_CATEGORY in t and is_in_month(t, year, month)
    ))


def month_categories(
    transactions: list[dict[str, Any]],
    year: int,
    month: int,
) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for t in transactions:
        if KEY_CATEGORY in t and is_in_month(t, year, month):
            full_category = t[KEY_CATEGORY]
            result[full_category] += t[KEY_AMOUNT]
    return dict(result)


def total_capital(transactions: list[dict[str, Any]]) -> float:
    total = 0
    for t in transactions:
        if KEY_CATEGORY in t:
            total += t[KEY_AMOUNT]
        else:
            total -= t[KEY_AMOUNT]
    return float(total)


def format_currency(val: float) -> str:
    return f"{val:.2f}"


def format_category_amount(val: float) -> str:
    return f"{int(val):,}" if val.is_integer() else f"{val:.2f}"


def format_details(categories: dict[str, float]) -> list[str]:
    if not categories:
        return ["Details (category: amount):"]
    lines = ["Details (category: amount):"]
    for idx, (cat, amt) in enumerate(categories.items()):   # index from 0
        lines.append(f"{idx}. {cat}: {format_category_amount(amt)}")
    return lines


def build_stats_message(report_date: str, stats: dict[str, Any]) -> str:
    lines = [
        f"Your statistics as of {report_date}:",
        f"Total capital: {format_currency(stats['total_capital'])} rubles",
    ]
    total_cap = stats["total_capital"]
    profit_word = "profit" if total_cap >= 0 else "loss"
    lines.append(f"This month, the {profit_word} amounted to {format_currency(abs(total_cap))} rubles.")
    lines.append(f"Income: {format_currency(stats['month_income'])} rubles")
    lines.append(f"Expenses: {format_currency(stats['month_expenses'])} rubles")
    lines.append("")
    lines.extend(format_details(stats.get(KEY_STATS_CATEGORIES, {})))
    return "\n".join([*lines, ""])


def stats_handler(report_date: str) -> str:
    report_tuple = extract_date(report_date)
    if report_tuple is None:
        return INCORRECT_DATE_MSG

    transactions = filter_transactions_up_to(report_tuple)
    year, month = report_tuple[2], report_tuple[1]

    stats = {
        "total_capital": total_capital(transactions),
        "month_income": month_expenses(transactions, year, month),
        "month_expenses": month_income(transactions, year, month),
        KEY_STATS_CATEGORIES: month_categories(transactions, year, month),
    }
    return build_stats_message(report_date, stats)


def process_income(args: list[str]) -> None:
    if len(args) != INCOME_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    try:
        amount = float(args[1].replace(",", "."))
    except ValueError:
        print(UNKNOWN_COMMAND_MSG)
        return
    result = income_handler(amount, args[2])
    print(result)


def process_cost(args: list[str]) -> None:
    if len(args) == COST_CATEGORIES_ARGS and args[1].lower() == "categories":
        print(cost_categories_handler())
        return
    if len(args) != COST_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    try:
        amount = float(args[2].replace(",", "."))
    except ValueError:
        print(UNKNOWN_COMMAND_MSG)
        return
    result = cost_handler(args[1], amount, args[3])
    print(result)


def process_stats(args: list[str]) -> None:
    if len(args) != STATS_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    result = stats_handler(args[1])
    print(result)


def unknown_command(_: list[str]) -> None:
    print(UNKNOWN_COMMAND_MSG)


COMMAND_HANDLERS = {
    "income": process_income,
    "cost": process_cost,
    "stats": process_stats,
}


def run_repl() -> None:
    while True:
        try:
            cmd_line = input().strip()
        except EOFError:
            break
        if not cmd_line:
            continue
        parts = cmd_line.split()
        command = parts[0].lower() if parts else ""
        handler = COMMAND_HANDLERS.get(command, unknown_command)
        handler(parts)


def main() -> None:
    run_repl()


if __name__ == "__main__":
    main()
