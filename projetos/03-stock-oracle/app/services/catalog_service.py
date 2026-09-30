import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.seeds import SEED_STRATEGIES
from app.models.strategy import StrategyModel, StrategyVersion


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def ensure_seed_catalog(db: Session) -> None:
    for seed in SEED_STRATEGIES:
        model = db.scalar(select(StrategyModel).where(StrategyModel.slug == seed.slug))
        if model is None:
            model = StrategyModel(
                slug=seed.slug,
                name=seed.name,
                description=seed.description,
            )
            db.add(model)
            db.flush()

        version = db.scalar(
            select(StrategyVersion).where(
                StrategyVersion.model_id == model.id,
                StrategyVersion.version == 1,
            )
        )
        if version is None:
            db.add(
                StrategyVersion(
                    model_id=model.id,
                    version=1,
                    name=f"{seed.name} v1",
                    hypothesis=seed.hypothesis,
                    code=seed.code,
                    parameters=json.dumps(seed.parameters, sort_keys=True),
                    code_hash=code_hash(seed.code),
                )
            )
    db.commit()


def list_models(db: Session) -> list[StrategyModel]:
    ensure_seed_catalog(db)
    return list(
        db.scalars(
            select(StrategyModel)
            .options(selectinload(StrategyModel.versions))
            .order_by(StrategyModel.name.asc())
        ).all()
    )


def get_model(db: Session, model_id: int) -> StrategyModel | None:
    ensure_seed_catalog(db)
    return db.scalar(
        select(StrategyModel)
        .options(selectinload(StrategyModel.versions))
        .where(StrategyModel.id == model_id)
    )


def get_active_versions(db: Session) -> list[StrategyVersion]:
    ensure_seed_catalog(db)
    return list(
        db.scalars(
            select(StrategyVersion)
            .where(StrategyVersion.is_active.is_(True))
            .order_by(StrategyVersion.model_id.asc(), StrategyVersion.version.asc())
        ).all()
    )


def get_versions(db: Session, version_ids: list[int] | None = None) -> list[StrategyVersion]:
    ensure_seed_catalog(db)
    stmt = select(StrategyVersion).where(StrategyVersion.is_active.is_(True))
    if version_ids:
        stmt = stmt.where(StrategyVersion.id.in_(version_ids))
    return list(db.scalars(stmt.order_by(StrategyVersion.id.asc())).all())


def mutate_version(db: Session, version_id: int) -> StrategyVersion:
    original = db.get(StrategyVersion, version_id)
    if original is None:
        raise ValueError("strategy version not found")

    latest_version = db.scalar(
        select(StrategyVersion.version)
        .where(StrategyVersion.model_id == original.model_id)
        .order_by(StrategyVersion.version.desc())
        .limit(1)
    )
    parameters = json.loads(original.parameters or "{}")
    mutated = _mutate_parameters(parameters)
    clone = StrategyVersion(
        model_id=original.model_id,
        version=int(latest_version or original.version) + 1,
        name=f"{original.name} mutacao",
        hypothesis=f"Mutacao manual assistida de: {original.hypothesis}",
        code=original.code,
        parameters=json.dumps(mutated, sort_keys=True),
        code_hash=code_hash(original.code),
        parent_version_id=original.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


def _mutate_parameters(parameters: dict[str, object]) -> dict[str, object]:
    mutated: dict[str, object] = {}
    for key, value in parameters.items():
        if isinstance(value, bool):
            mutated[key] = value
        elif isinstance(value, int):
            mutated[key] = max(1, int(round(value * 1.2)))
        elif isinstance(value, float):
            mutated[key] = round(value * 1.1, 6)
        else:
            mutated[key] = value
    return mutated
