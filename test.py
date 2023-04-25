from typing import Optional, Any

from pydantic import BaseModel, Field


def test_function(*args, **kwargs):
    return ComparableModel.eq(args[0], args[1])


class ComparableModel(BaseModel):

    @classmethod
    def eq(cls, current_value: Any, other_value: Any):
        if not current_value == other_value:
            return False, f"{current_value} != {other_value}"
        return True, ""

    @classmethod
    def percent(cls, current_value: Any, other_value: Any, percent):
        percent_diff = abs((other_value * 100 / current_value) - 100.0)
        if percent_diff > percent:
            return False, f"{current_value} differs {other_value} by more than {percent} percent. ({percent_diff:.2f})"
        return True, ""

    @classmethod
    def comparator(cls, field: Field):
        comparator = field.field_info.extra.get("extra", {}).get("comparator")
        comparator_kwargs = field.field_info.extra.get("extra", {}).get("comparator_kwargs", {})
        if callable(comparator):
            return comparator, comparator_kwargs
        if comparator == "eq":
            return cls.eq, comparator_kwargs
        if comparator == "percent":
            return cls.percent, comparator_kwargs

    def __eq__(self, other: 'ComparableModel'):
        comparison_result = {}
        for field in self.__fields__.values():
            field_comparator, comparator_kwargs = self.comparator(field)
            field_comparison_result = field_comparator(
                getattr(self, field.alias),
                getattr(other, field.alias),
                **comparator_kwargs
            )
            comparison_result[field.alias] = {
                "comparable": field_comparison_result[0],
                "message": f"{field.alias}: {field_comparison_result[1]}"
            }

        return ComparisonResult(self, other, comparison_result)


class User(ComparableModel):
    id: int = Field(..., extra={"comparator": "eq"})
    name: str = Field(..., extra={"comparator": "eq"})
    title: Optional[str] = Field(None, extra={"comparator": test_function})
    score: float = Field(10.0, extra={"comparator": "percent", "comparator_kwargs": {"percent": 10}})


class ComparisonResult:

    def __init__(self, obj, other, comparison_result: dict):
        self.obj = obj
        self.other = other
        self.result = comparison_result

        self.errors = []

        for value in self.result.values():
            if not value["comparable"]:
                self.errors.append(value["message"])

    def __bool__(self):
        return len(self.errors) == 0

    def __str__(self):
        if self.errors:
            return f"{self.obj} and {self.other} are NOT comparable. {' '.join(self.errors)}"
        return f"{self.obj} and {self.other} are comparable"

    def __repr__(self):
        return self.__str__()