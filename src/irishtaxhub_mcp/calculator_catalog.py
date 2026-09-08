"""Calculator names, API paths, descriptions, and website URL mappings."""

from typing import Dict, Literal

from .attribution import _site_url

CALCULATORS: Dict[str, Dict[str, str]] = {
    "base": {
        "path": "/v1/tax/calculators/base",
        "summary": (
            "Calculate income tax, USC, and PRSI for a given salary."
            " Supports single/married, multiple employments, tax credits."
        ),
    },
    "refund": {
        "path": "/v1/tax/calculators/refund",
        "summary": "Estimate a PAYE tax refund by comparing tax paid vs tax owed.",
    },
    "tax-free-earnings": {
        "path": "/v1/tax/calculators/tax-free-earnings",
        "summary": (
            "Calculate tax-free earnings date for someone"
            " arriving in or departing Ireland mid-year."
        ),
    },
    "refund-for-move-date": {
        "path": "/v1/tax/calculators/refund-for-move-date",
        "summary": "Calculate tax refund for a specific move date (arriving/departing Ireland).",
    },
    "net-to-gross": {
        "path": "/v1/tax/calculators/net-to-gross",
        "summary": "Reverse-calculate the gross salary needed to achieve a target net income.",
    },
    "rental-income": {
        "path": "/v1/tax/calculators/rental-income",
        "summary": (
            "Calculate tax on rental income including allowable"
            + " expenses and mortgage interest."
        ),
    },
    "self-employed": {
        "path": "/v1/tax/calculators/self-employed",
        "summary": (
            "Calculate tax for self-employed individuals including PRSI Class S and expenses."
        ),
    },
    "capital-gains": {
        "path": "/v1/tax/calculators/capital-gains",
        "summary": "Calculate Capital Gains Tax (CGT) on asset disposals at 33%.",
    },
    "share-options": {
        "path": "/v1/tax/calculators/share-options",
        "summary": "Calculate tax on share option exercise (RTSO — Relevant Tax on Share Options).",
    },
    "share-options-cgt": {
        "path": "/v1/tax/calculators/share-options-cgt",
        "summary": "Calculate CGT on the sale of shares acquired via share options.",
    },
    "work-from-home-expense": {
        "path": "/v1/tax/calculators/work-from-home-expense",
        "summary": "Calculate e-worker tax relief for remote working expenses.",
    },
    "avc": {
        "path": "/v1/tax/calculators/avc",
        "summary": "Calculate maximum Additional Voluntary Contribution (AVC) and tax relief.",
    },
    "pension-value": {
        "path": "/v1/tax/calculators/pension-value",
        "summary": "Estimate pension fund value at retirement based on contributions and growth.",
    },
    "future-fund": {
        "path": "/v1/tax/calculators/future-fund",
        "summary": "Estimate future investment fund value with regular contributions.",
    },
    "mortgage": {
        "path": "/v1/tax/calculators/mortgage",
        "summary": "Calculate monthly mortgage repayments, total interest, and amortisation.",
    },
    "redundancy-tax": {
        "path": "/v1/tax/calculators/redundancy-tax",
        "summary": "Calculate tax on redundancy and termination payments (SCSB, top-up, etc.).",
    },
    "mortgage-affordability": {
        "path": "/v1/tax/calculators/mortgage-affordability",
        "summary": "Calculate maximum mortgage you can afford based on income and LTI rules.",
    },
    "cat": {
        "path": "/v1/tax/calculators/cat",
        "summary": "Calculate Capital Acquisitions Tax (CAT) on gifts and inheritances.",
    },
    "sarp": {
        "path": "/v1/tax/calculators/sarp",
        "summary": (
            "Calculate SARP (Special Assignee Relief Programme) tax relief for foreign assignees."
        ),
    },
    "vat3": {
        "path": "/v1/tax/calculators/vat3",
        "summary": "Calculate VAT3 return figures for VAT-registered businesses.",
    },
}

CalculatorName = Literal[
    "base",
    "refund",
    "tax-free-earnings",
    "refund-for-move-date",
    "net-to-gross",
    "rental-income",
    "self-employed",
    "capital-gains",
    "share-options",
    "share-options-cgt",
    "work-from-home-expense",
    "avc",
    "pension-value",
    "future-fund",
    "mortgage",
    "redundancy-tax",
    "mortgage-affordability",
    "cat",
    "sarp",
    "vat3",
]

_CALC_LIST = "\n".join(f"  - {name}: {info['summary']}" for name, info in CALCULATORS.items())

_CALCULATE_TAX_DESC = f"""Run an Irish tax calculator and return the full result.

Available calculators:
{_CALC_LIST}

Pass the calculator name and its required inputs. \
Use `get_calculator_schema` first if you need to know \
the exact input fields for a calculator.

Common examples:

base (income tax): {{"marital_status": "single", \
"employment_income": {{"income": 75000, "period": "annual"}}, \
"year": 2026}}

marital_status options: single, widow, \
married_one_income, married_two_income

refund: {{"marital_status": "single", \
"employment_income": {{"income": 50000, "tax_paid": 18000}}, \
"year": 2026}}

capital-gains: {{"sale_price": 400000, \
"purchase_price": 250000, "purchase_date": "2018-03-15", \
"sale_date": "2026-06-01", "year": 2026}}

mortgage: {{"home_price": 400000, "deposit": 40000, \
"loan_term_years": 30, "interest_rate": 4.0}}

work-from-home-expense: {{"electricity_costs": 1200, \
"heating_costs": 800, "internet_costs": 600, \
"tax_year": 2026, "total_earnings": 75000, \
"days_working_from_home": 200}}

avc: {{"age": 45, "gross_earnings": 100000, "year": 2026}}

share-options: {{"share_option_price": 10, \
"sale_price": 50, "number_of_units": 1000}}

redundancy-tax: {{"employment_start_date": "2010-01-01", \
"employment_end_date": "2026-06-01", "gross_weekly_pay": 1500}}

mortgage-affordability: {{"buyer_type": "first_time_buyer", \
"gross_annual_income_1": 75000, "savings": 50000}}"""

_STATS_SLUG_MAP: Dict[str, str] = {
    "base": "salary-after-tax",
    "refund": "refund",
    "tax-free-earnings": "arriving-ireland-tax-savings",
    "refund-for-move-date": "arriving-ireland-tax-savings",
    "net-to-gross": "net-to-gross",
    "rental-income": "rental-income",
    "self-employed": "self-employed-income",
    "capital-gains": "capital-gains-tax",
    "share-options": "employee-share-options",
    "share-options-cgt": "share-sale-cgt",
    "work-from-home-expense": "work-from-home",
    "avc": "additional-voluntary-contribution",
    "pension-value": "pension-value",
    "future-fund": "auto-enrolment",
    "mortgage": "mortgage-payments",
    "redundancy-tax": "redundancy-tax",
    "mortgage-affordability": "mortgage-affordability",
    "cat": "cat",
    "sarp": "sarp",
    "vat3": "vat3",
}


def _calculator_url(calculator_name: str) -> str:
    slug = _STATS_SLUG_MAP.get(calculator_name, calculator_name)
    return _site_url(f"/calculators/{slug}")
