from typing import TypeAlias
from uuid import UUID

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list[JsonScalar] | dict[str, JsonScalar]
JsonObject: TypeAlias = dict[str, JsonValue]
JsonObjectList: TypeAlias = list[JsonObject]
ContextValue: TypeAlias = JsonValue | JsonObjectList
ContextObject: TypeAlias = dict[str, ContextValue]
ScopeFilter: TypeAlias = dict[str, JsonScalar]
I18nText: TypeAlias = dict[str, str]
SlugEntityMap: TypeAlias = dict[str, UUID]
