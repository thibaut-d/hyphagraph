"""
Export API endpoints.

Provides data export functionality in multiple formats.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from typing import Literal

from app.api.service_dependencies import get_export_service, get_typedb_export_service
from app.services.export_service import ExportService
from app.services.typedb_export_service import TypeDBExportService
from app.dependencies.auth import get_current_user
from app.models.user import User


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
    content = await service.export_relations(format, include_metadata)

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


@router.get("/typedb-full")
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
