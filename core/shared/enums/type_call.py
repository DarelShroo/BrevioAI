from enum import Enum


class TypeCall(Enum):
    SUMMARY = "summary"
    DIRECT = "direct"
    REDUCE = "reduce"
    FORMAT = "format"
    CONNECTIVITY = "connectivity"
    # Legacy value kept so historical logs.json entries still deserialize.
    POSTPROCESSING = "postprocessing"
