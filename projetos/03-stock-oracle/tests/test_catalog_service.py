import json

from app.services.catalog_service import ensure_seed_catalog, get_active_versions, mutate_version


def test_seed_catalog_creates_active_versions(db_session):
    ensure_seed_catalog(db_session)

    versions = get_active_versions(db_session)

    assert len(versions) >= 3
    assert all(version.code_hash for version in versions)


def test_mutate_version_creates_child_with_changed_parameters(db_session):
    ensure_seed_catalog(db_session)
    original = get_active_versions(db_session)[0]
    original_params = json.loads(original.parameters)

    clone = mutate_version(db_session, original.id)

    assert clone.parent_version_id == original.id
    assert clone.version == original.version + 1
    assert json.loads(clone.parameters) != original_params
