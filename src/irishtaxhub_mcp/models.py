from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, confloat, conint


class MaritalStatus(str, Enum):
    single = "single"
    married_one_income = "married_one_income"
    married_two_income = "married_two_income"


class IncomeType(str, Enum):
    one = "one"
    two = "two"


class Period(str, Enum):
    annual = "annual"
    monthly = "monthly"
    weekly = "weekly"


class Direction(str, Enum):
    arriving = "arriving"
    departing = "departing"


class EmploymentOverview(BaseModel):
    income: float = 0
    pension_contribution: confloat(ge=0, le=100) = 0
    tax_paid: float = 0


class EmploymentIncome(BaseModel):
    income: float = 0
    other_income_annual: float = 0
    bonus_income_annual: float = 0
    non_cash_benefit: float = 0
    pension_contribution: confloat(ge=0, le=100) = 0
    voluntary_deductions: float = 0
    period: Period = Period.annual


class Credits(BaseModel):
    rent_paid: float = 0
    medical_dental_expenses: float = 0
    tuition_fees: float = 0


class SimpleToggleCredit(BaseModel):
    eligible: bool = False


class CountCredit(BaseModel):
    eligible: bool = False
    num_claiming: conint(ge=0) = 0


class WidowedParentCredit(BaseModel):
    eligible: bool = False
    years_since_bereavement: conint(ge=1, le=5) = 0


class MedicalInsurancePolicy(BaseModel):
    adults: conint(ge=0, le=200) = 0
    children: conint(ge=0, le=100) = 0


class EmployerMedicalInsuranceCredit(BaseModel):
    eligible: bool = False
    policies: List[MedicalInsurancePolicy] = Field(default_factory=list)


class FixedCredits(BaseModel):
    marital_status: Optional[MaritalStatus] = None
    single_person_child_carer: Optional[SimpleToggleCredit] = None
    home_carer: Optional[SimpleToggleCredit] = None
    incapacitated_child: Optional[CountCredit] = None
    dependent_relative: Optional[CountCredit] = None
    employer_medical_insurance: Optional[EmployerMedicalInsuranceCredit] = None
    blind_credit: Optional[CountCredit] = None
    widowed_parent_credit: Optional[WidowedParentCredit] = None
    widowed_credit: Optional[SimpleToggleCredit] = None
    age_credit: Optional[CountCredit] = None
    guide_dog_credit: Optional[CountCredit] = None


class BaseTaxRequest(BaseModel):
    marital_status: MaritalStatus
    employment_income: EmploymentIncome
    spouse_employment_income: Optional[EmploymentIncome] = None
    additional_employment_income: Optional[List[EmploymentIncome]] = None
    additional_spouse_employment_income: Optional[List[EmploymentIncome]] = None
    income_type: Optional[IncomeType] = None
    year: Optional[int] = Field(default=None, ge=2024, le=2034)
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    age: Optional[int] = Field(default=None, ge=0, le=120)
    spouse_age: Optional[int] = Field(default=None, ge=0, le=120)
    fixed_credits: Optional[FixedCredits] = None
    spending_credits: Optional[Credits] = None


class TaxRefundRequest(BaseModel):
    marital_status: MaritalStatus
    employment_income: Optional[EmploymentOverview] = None
    spouse_employment_income: Optional[EmploymentOverview] = None
    additional_employment_income: Optional[List[EmploymentOverview]] = None
    additional_spouse_employment_income: Optional[List[EmploymentOverview]] = None
    year: Optional[int] = Field(default=2024, ge=2024, le=2034)
    spending_credits: Optional[Credits] = None
    income_type: Optional[IncomeType] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    spouse_age: Optional[int] = Field(default=None, ge=0, le=120)
    fixed_credits: Optional[FixedCredits] = None


class TaxFreeEarningsRequest(BaseModel):
    marital_status: MaritalStatus
    direction: Direction
    gross_annual_salary: float = Field(ge=1)
    year: int = Field(ge=2024, le=2034)
    income_type: Optional[IncomeType] = None
