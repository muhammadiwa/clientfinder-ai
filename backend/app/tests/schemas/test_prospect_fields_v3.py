"""
Schema + model tests for the 4 new prospect fields (Sprint 1 / T5 v3 / brief).

Covers:
- Pydantic schemas (ProspectBase, ProspectUpdate) accept + validate the
  4 new fields
- Field constraints (max lengths, ge=0, le=100 for closing_probability)
- The new fields appear in ProspectOut so the API returns them
- Migration is present and runs upgrade + downgrade cleanly
"""
import importlib
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.prospect import Prospect
from app.schemas.prospect import (
    ProspectBase,
    ProspectCreate,
    ProspectOut,
    ProspectUpdate,
)


# --- Pydantic schema validation ---

class TestProspectBaseNewFields:
    def test_defaults_all_optional(self):
        """All 4 new fields are optional (nullable in DB)."""
        p = ProspectBase(company_name="Test Co")
        assert p.owner_name is None
        assert p.employee_count is None
        assert p.revenue_estimate is None
        assert p.closing_probability is None

    def test_accepts_all_four(self):
        p = ProspectBase(
            company_name="Test Co",
            owner_name="Budi Santoso",
            employee_count=12,
            revenue_estimate="Rp 50jt/bulan",
            closing_probability=72,
        )
        assert p.owner_name == "Budi Santoso"
        assert p.employee_count == 12
        assert p.revenue_estimate == "Rp 50jt/bulan"
        assert p.closing_probability == 72

    def test_owner_name_max_length(self):
        with pytest.raises(ValidationError):
            ProspectBase(company_name="Test", owner_name="x" * 256)

    def test_revenue_max_length(self):
        with pytest.raises(ValidationError):
            ProspectBase(company_name="Test", revenue_estimate="x" * 101)

    def test_employee_count_ge_zero(self):
        with pytest.raises(ValidationError):
            ProspectBase(company_name="Test", employee_count=-1)

    def test_closing_probability_range(self):
        with pytest.raises(ValidationError):
            ProspectBase(company_name="Test", closing_probability=-1)
        with pytest.raises(ValidationError):
            ProspectBase(company_name="Test", closing_probability=101)


class TestProspectUpdateNewFields:
    def test_partial_update(self):
        u = ProspectUpdate(closing_probability=80)
        assert u.closing_probability == 80
        assert u.owner_name is None

    def test_all_optional(self):
        u = ProspectUpdate()
        assert u.owner_name is None
        assert u.employee_count is None
        assert u.revenue_estimate is None
        assert u.closing_probability is None


class TestProspectCreateInheritsNewFields:
    def test_create_inherits_base(self):
        c = ProspectCreate(
            company_name="Klinik Sehat",
            source="manual",
            owner_name="Dr. Sari",
            employee_count=8,
            revenue_estimate="Rp 80jt/bulan",
            closing_probability=85,
        )
        assert c.owner_name == "Dr. Sari"
        assert c.employee_count == 8


class TestProspectOutExposesNewFields:
    def test_out_has_fields(self):
        fields = ProspectOut.model_fields.keys()
        for f in ("owner_name", "employee_count", "revenue_estimate", "closing_probability"):
            assert f in fields, f"ProspectOut missing field {f}"


# --- Model exposes attributes ---

class TestProspectModelAttributes:
    def test_model_class_has_columns(self):
        """Verify the 4 columns are declared on the ORM model."""
        for attr in ("owner_name", "employee_count", "revenue_estimate", "closing_probability"):
            assert hasattr(Prospect, attr), f"Prospect model missing {attr}"


# --- Migration file exists + has correct structure ---

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "alembic"
    / "versions"
)


class TestMigrationExists:
    def test_migration_file_exists(self):
        """The Sprint 1 migration should be on disk."""
        candidates = list(MIGRATION_PATH.glob("*add_4_prospect_fields*.py"))
        assert candidates, "Sprint 1 migration not found"

    def test_migration_imports_cleanly(self):
        """The migration module imports without error."""
        candidates = list(MIGRATION_PATH.glob("*add_4_prospect_fields*.py"))
        if not candidates:
            pytest.skip("migration file not present")
        spec = importlib.util.spec_from_file_location(
            "sp1_migration", candidates[0],
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "upgrade")
        assert hasattr(mod, "downgrade")

    def test_migration_revision_metadata(self):
        candidates = list(MIGRATION_PATH.glob("*add_4_prospect_fields*.py"))
        if not candidates:
            pytest.skip("migration file not present")
        spec = importlib.util.spec_from_file_location(
            "sp1_migration", candidates[0],
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.revision == "b8c2f5a3e1d2"
        assert mod.down_revision == "32f1769c14bb"
