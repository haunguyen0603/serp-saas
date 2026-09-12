"""M4 engine regression harness. HTTP enqueue semantics have dedicated M5 tests."""

from uuid import UUID

import jwt
from fastapi import FastAPI
from httpx import Response
from pydantic import ValidationError

from app.core.errors import AppError
from app.dependencies.business import get_serp_provider_dependency
from app.schemas.rank_check import ProjectRankCheckRequest, RankCheckRequest
from app.services.rank_checks import RankCheckExecutionService


async def execute_engine(
    app: FastAPI, path: str, *, headers: dict[str, str], json: dict
) -> Response:
    claims = jwt.decode(
        headers["Authorization"][7:],
        app.state.settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
    )
    user_id = UUID(claims["sub"])
    parts = path.split("/")
    project_id = UUID(parts[4])
    provider = app.dependency_overrides[get_serp_provider_dependency]()
    service = RankCheckExecutionService(
        app.state.session_factory, provider, app.state.settings
    )
    try:
        if "keywords" in parts:
            RankCheckRequest.model_validate(json)
            result = await service.run_keyword(project_id, UUID(parts[6]), user_id)
        else:
            result = await service.run_project(
                project_id, user_id, ProjectRankCheckRequest.model_validate(json)
            )
        return Response(201, json=result.model_dump(mode="json"))
    except AppError as error:
        return Response(
            error.status, json={"error": {"code": error.code, "message": error.message}}
        )
    except ValidationError:
        return Response(422, json={"error": {"code": "VALIDATION_ERROR"}})
