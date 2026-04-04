"""
Export API endpoints.

Provides data export functionality in multiple formats.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from typing import Literal, List, Optional

from app.api.service_dependencies import get_export_service, get_typedb_export_service
from app.services.export_service import ExportService
from app.services.typedb_export_service import TypeDBExportService
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.typedb_export import TypeDBExportBundle


router = APIRouter(tags=["export"])


@router.get("/entities")
async def export_entities(
    format: Literal["json", "csv", "rdf"] = Query("json", description="Export format"),
    include_metadata: bool = Query(True, description="Include creation dates and provenance"),
    service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export all entities in specified format.

    Formats:
    - json: Complete JSON with all fields
    - csv: Spreadsheet-compatible tabular format
    - rdf: RDF Turtle for semantic web interoperability

    Returns a downloadable file.
    """
    content = await service.export_entities(format, include_metadata)

    # Set appropriate content type and filename
    content_types = {
        "json": "application/json",
        "csv": "text/csv",
        "rdf": "text/turtle"
    }

    extensions = {
        "json": "json",
        "csv": "csv",
        "rdf": "ttl"
    }

    return Response(
        content=content,
        media_type=content_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="entities.{extensions[format]}"'
        }
    )


@router.get("/relations")
async def export_relations(
    format: Literal["json", "csv", "rdf"] = Query("json", description="Export format"),
    include_metadata: bool = Query(True, description="Include creation dates and provenance"),
    kind: Optional[List[str]] = Query(None, description="Filter by source kind"),
    year_min: Optional[int] = Query(None, description="Filter by minimum year"),
    year_max: Optional[int] = Query(None, description="Filter by maximum year"),
    trust_level_min: Optional[float] = Query(None, description="Filter by minimum trust level", ge=0.0, le=1.0),
    trust_level_max: Optional[float] = Query(None, description="Filter by maximum trust level", ge=0.0, le=1.0),
    search: Optional[str] = Query(None, description="Search in source title/authors/origin"),
    domain: Optional[List[str]] = Query(None, description="Filter by source domain"),
    role: Optional[List[str]] = Query(None, description="Filter by source graph role"),
    service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export all relations with their roles.

    Formats:
    - json: Complete JSON with all fields and roles
    - csv: Flattened tabular format (subject → relation → object)
    - rdf: RDF Turtle for semantic web

    Returns a downloadable file.
    """
    content = await service.export_relations(
        format,
        include_metadata,
        kind=kind,
        year_min=year_min,
        year_max=year_max,
        trust_level_min=trust_level_min,
        trust_level_max=trust_level_max,
        search=search,
        domain=domain,
        role=role,
    )

    content_types = {
        "json": "application/json",
        "csv": "text/csv",
        "rdf": "text/turtle"
    }

    extensions = {
        "json": "json",
        "csv": "csv",
        "rdf": "ttl"
    }

    return Response(
        content=content,
        media_type=content_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="relations.{extensions[format]}"'
        }
    )


@router.get("/sources")
async def export_sources(
    format: Literal["json", "csv"] = Query("json", description="Export format"),
    include_metadata: bool = Query(True, description="Include creation dates"),
    kind: Optional[List[str]] = Query(None, description="Filter by source kind"),
    year_min: Optional[int] = Query(None, description="Filter by minimum year"),
    year_max: Optional[int] = Query(None, description="Filter by maximum year"),
    trust_level_min: Optional[float] = Query(None, description="Filter by minimum trust level", ge=0.0, le=1.0),
    trust_level_max: Optional[float] = Query(None, description="Filter by maximum trust level", ge=0.0, le=1.0),
    search: Optional[str] = Query(None, description="Search in title/authors"),
    domain: Optional[List[str]] = Query(None, description="Filter by domain"),
    role: Optional[List[str]] = Query(None, description="Filter by graph role"),
    service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export sources in specified format.

    Accepts the same filter parameters as the sources list endpoint so that
    the export reflects the currently visible (filtered) sources.
    """
    content = await service.export_sources(
        format, include_metadata,
        kind=kind, year_min=year_min, year_max=year_max,
        trust_level_min=trust_level_min, trust_level_max=trust_level_max,
        search=search, domain=domain, role=role,
    )

    content_types = {"json": "application/json", "csv": "text/csv"}
    extensions = {"json": "json", "csv": "csv"}

    return Response(
        content=content,
        media_type=content_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="sources.{extensions[format]}"'
        },
    )


@router.get("/full-graph")
async def export_full_graph(
    include_metadata: bool = Query(True, description="Include creation dates and provenance"),
    service: ExportService = Depends(get_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export complete knowledge graph (entities + relations + sources).

    Format: JSON only (complete graph representation)

    Returns a self-contained JSON file that includes:
    - All entities
    - All relations
    - All sources
    - Complete metadata

    This export can be reimported into another HyphaGraph instance.
    """
    content = await service.export_full_graph("json", include_metadata)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="hyphagraph-full-export.json"'
        }
    )


@router.get("/typedb-schema")
async def export_typedb_schema(
    service: TypeDBExportService = Depends(get_typedb_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export TypeDB schema (TypeQL format).
    
    Returns schema definition for importing into TypeDB.
    Includes entity types, relation types with semantic roles.
    """
    schema = await service.export_schema()
    
    return Response(
        content=schema,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=\"hyphagraph-schema.tql\""
        }
    )


@router.get("/typedb-data")
async def export_typedb_data(
    limit: int = Query(None, description="Limit entities/relations exported"),
    service: TypeDBExportService = Depends(get_typedb_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export TypeDB data (TypeQL insert statements).
    
    Returns data in TypeQL format for importing into TypeDB.
    """
    data = await service.export_data(limit=limit)
    
    return Response(
        content=data,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=\"hyphagraph-data.tql\""
        }
    )


@router.get("/typedb-full", response_model=TypeDBExportBundle)
async def export_typedb_full(
    service: TypeDBExportService = Depends(get_typedb_export_service),
    current_user: User = Depends(get_current_user),
):
    """
    Export complete TypeDB package (schema + data as JSON).
    
    Returns both schema and data for complete TypeDB setup.
    """
    result = await service.export_full()
    
    return result
