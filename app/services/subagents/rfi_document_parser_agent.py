import logging
import re
from typing import Any, List
from app.schemas.phase1_agent_schemas import DocumentParsingTaskResult

logger = logging.getLogger("conductor.services.subagents.rfi_document_parser")


class RfiDocumentParserSubAgent:
    """
    Sub-Agent 1: Specialized Multi-Format Document Ingestion & Structural Parser.
    Extracts raw text blocks, table elements, multi-tab layout hints, and report title metadata.
    Handles unhappy path input resilience (gibberish, empty, or malformed user text).
    """

    @classmethod
    async def parse_document(cls, raw_input: str) -> DocumentParsingTaskResult:
        """Parses unstructured text, document URLs, or raw briefing packets into structured layout blocks."""
        logger.info("RfiDocumentParserSubAgent processing document intake...")

        if not raw_input or not raw_input.strip():
            return DocumentParsingTaskResult(
                parsed_layout_blocks=[],
                extracted_tables=[],
                raw_text_cleaned="",
                detected_report_title=None,
                is_multi_tab_spreadsheet=False,
                status="warning",
                error_message="Empty input document provided. Defaulting to defensive fallback mode.",
            )

        cleaned_text = raw_input.strip()
        lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]

        # Identify potential report title
        detected_title = None
        for line in lines[:5]:
            if any(kw in line.lower() for kw in ["gartner", "forrester", "idc", "magic quadrant", "wave", "marketscape", "devsecops", "cnap"]):
                detected_title = line
                break

        # Layout blocks extraction
        layout_blocks = [line for line in lines if len(line) > 10]

        # Extract table structures (lines containing pipe symbols or tab delimiters)
        extracted_tables = []
        table_rows = [line for line in lines if "|" in line or "\t" in line]
        if table_rows:
            extracted_tables.append({"type": "delimited_table", "rows": table_rows})

        # Multi-tab spreadsheet heuristic check
        is_spreadsheet = any(kw in cleaned_text.lower() for kw in ["sheet", "tab", "worksheet", "csv", "xlsx", "google.com/spreadsheets"])

        # Check for unreadable/gibberish text resilience
        has_meaningful_content = any(
            kw in cleaned_text.lower() for kw in ["ga", "revenue", "cagr", "customer", "criteria", "feature", "capability", "inclusion", "exclusion", "gartner", "forrester", "idc", "devsecops", "cnap"]
        )

        status = "success"
        err_msg = None
        if not has_meaningful_content and len(cleaned_text) < 50:
            status = "warning"
            err_msg = "Unrecognized document format or insufficient analyst criteria context detected."

        return DocumentParsingTaskResult(
            parsed_layout_blocks=layout_blocks,
            extracted_tables=extracted_tables,
            raw_text_cleaned=cleaned_text,
            detected_report_title=detected_title,
            is_multi_tab_spreadsheet=is_spreadsheet,
            status=status,
            error_message=err_msg,
        )
