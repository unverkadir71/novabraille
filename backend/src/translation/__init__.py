# Braille translation engine
#
# Public API surface for the translation module.
# Plan v9 referansı: Faz 2 — Çeviri Çekirdeği

from __future__ import annotations

from .contraction_config import (
    CONTRACTION_PROFILES,
    ContractionLevel,
    ContractionProfile,
    get_all_contraction_profiles,
    get_contraction_profile,
)
from .exceptions import (
    EmptyInputError,
    TableCompileError,
    TableNotFoundError,
    TranslationError,
    TranslationFailedError,
)
from .file_processor import (
    FileProcessingError,
    FileProcessor,
    FileTooLargeError,
    InputFormat,
    PandocConversionError,
    PandocNotFoundError,
    PDFExtractionError,
    UnsupportedFormatError,
)
from .liblouis import LiblouisWrapper, TranslationResult, liblouis_wrapper
from .output_formats import (
    BRFProducer,
    BRLProducer,
    DisplayProducer,
    OutputFormat,
    OutputMode,
    PageLayout,
    get_producer,
)
from .table_manifest import (
    TableAllowlist,
    TableManifest,
    TableManifestEntry,
    TableName,
    get_allowlist,
    get_manifest,
)
from .types import (
    LANGUAGE_TABLE_MAP,
    TURKISH_TABLES,
    BrailleGrade,
    TranslationDirection,
    TranslationMode,
    Typeform,
)

__all__ = [
    # Wrapper
    "LiblouisWrapper",
    "liblouis_wrapper",
    "TranslationResult",
    # Manifest
    "TableManifest",
    "TableManifestEntry",
    "TableName",
    "TableAllowlist",
    "get_manifest",
    "get_allowlist",
    # Types
    "BrailleGrade",
    "TranslationDirection",
    "TranslationMode",
    "Typeform",
    "TURKISH_TABLES",
    "LANGUAGE_TABLE_MAP",
    # File Processor
    "FileProcessor",
    "InputFormat",
    "FileProcessingError",
    "UnsupportedFormatError",
    "PandocNotFoundError",
    "PandocConversionError",
    "PDFExtractionError",
    "FileTooLargeError",
    # Output Formats
    "OutputMode",
    "OutputFormat",
    "BRFProducer",
    "BRLProducer",
    "DisplayProducer",
    "PageLayout",
    "get_producer",
    # Contraction
    "ContractionProfile",
    "ContractionLevel",
    "CONTRACTION_PROFILES",
    "get_contraction_profile",
    "get_all_contraction_profiles",
    # Exceptions
    "TranslationError",
    "TableNotFoundError",
    "TableCompileError",
    "EmptyInputError",
    "TranslationFailedError",
]
