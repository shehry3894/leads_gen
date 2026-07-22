"""
Data normalization and validation utilities.

This module provides functions to:
- Define and enforce a canonical data model with fixed column schema
- Normalize and clean scraped business data
- Deduplicate entries by website or (business name + address)
- Sanitize strings for Excel compatibility
"""

import logging
import re
from typing import Any

import pandas as pd

logger = logging.getLogger("leads_gen")

# Canonical column schema with fixed order
CANONICAL_COLUMNS = [
    "Name",
    "Google Maps Link",
    "Address",
    "Phone",
    "WhatsApp",
    "Website",
    "Rating",
    "Review Count",
    "Facebook",
    "Instagram",
    "Twitter",
    "LinkedIn",
    "YouTube",
    "Pinterest",
    "TikTok",
    "Threads",
    "Snapchat",
    "Emails",
    "Scraped Time",
]


def normalize_empty_value(value: Any) -> str:
    """
    Normalize empty/missing values to empty string.

    Args:
        value: The value to normalize

    Returns:
        Empty string if value is None, "N/A", or empty; otherwise the value as string
    """
    if (
        value is None
        or value == "N/A"
        or value == ""
        or (isinstance(value, float) and pd.isna(value))
    ):
        return ""
    return str(value).strip()


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number by removing common formatting and keeping only digits and essential characters.

    Args:
        phone: Raw phone number string

    Returns:
        Normalized phone number
    """
    if not phone or phone == "N/A":
        return ""

    # Remove common separators and whitespace, keep +, digits, and parentheses
    normalized = re.sub(r"[\s\-\.\u00a0]", "", phone)
    # Remove any non-phone characters except +, digits, and parentheses
    normalized = re.sub(r"[^\d\+\(\)]", "", normalized)
    return normalized.strip()


def sanitize_for_excel(value: str) -> str:
    """
    Sanitize string for Excel compatibility.

    - Remove or replace characters that cause Excel issues
    - Trim excessive whitespace
    - Handle newlines and tabs

    Args:
        value: String to sanitize

    Returns:
        Sanitized string safe for Excel
    """
    if not value:
        return ""

    # Strip control chars first — Python's \s matches \x1c-\x1f under
    # re.UNICODE, so if the whitespace collapse ran first those bytes
    # would silently turn into spaces instead of being removed.
    value = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip()
    return value


def normalize_business_record(record: dict[str, Any]) -> dict[str, str]:
    """
    Normalize a single business record.

    Args:
        record: Raw business data dictionary

    Returns:
        Normalized business data dictionary with canonical schema
    """
    normalized = {}

    for col in CANONICAL_COLUMNS:
        raw_value = record.get(col, "")

        # Special handling for phone number
        if col == "Phone":
            normalized[col] = normalize_phone_number(str(raw_value))
        # Special handling for list fields (convert to comma-separated string)
        elif col == "Emails" and isinstance(raw_value, list):
            normalized[col] = ", ".join(str(e).strip() for e in raw_value if e)
        else:
            # General normalization: empty values and sanitization
            normalized[col] = sanitize_for_excel(normalize_empty_value(raw_value))

    return normalized


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a DataFrame of business data.

    - Ensures canonical column schema
    - Normalizes all values
    - Trims whitespace
    - Sanitizes for Excel

    Args:
        df: Raw DataFrame

    Returns:
        Normalized DataFrame with canonical schema
    """
    if df.empty:
        # Return empty DataFrame with canonical columns
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    # Normalize each record
    normalized_records = [normalize_business_record(row.to_dict()) for _, row in df.iterrows()]
    normalized_df = pd.DataFrame(normalized_records, columns=CANONICAL_COLUMNS)

    logger.info(f"Normalized {len(normalized_df)} business records")
    return normalized_df


def deduplicate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate business records.

    Deduplication strategy:
    1. Primary key: Website (if available and not empty)
    2. Fallback key: (Business Name + Address)

    Keeps the first occurrence of each unique business.

    Args:
        df: DataFrame to deduplicate

    Returns:
        Deduplicated DataFrame
    """
    if df.empty:
        return df

    original_count = len(df)

    def make_dedup_key(row):
        website = str(row.get("Website", "")).strip().lower()
        if website and website != "n/a":
            return f"website:{website}"
        name = str(row.get("Name", "")).strip().lower()
        address = str(row.get("Address", "")).strip().lower()
        return f"name_addr:{name}|{address}"

    # Work on a copy so callers keep the DataFrame they gave us intact.
    working = df.copy()
    working["_dedup_key"] = working.apply(make_dedup_key, axis=1)
    deduped_df = working.drop_duplicates(subset=["_dedup_key"], keep="first").drop(
        columns=["_dedup_key"]
    )

    duplicates_removed = original_count - len(deduped_df)
    if duplicates_removed > 0:
        logger.info(
            f"Removed {duplicates_removed} duplicate business records (original: {original_count}, final: {len(deduped_df)})"
        )
    else:
        logger.info(f"No duplicates found (total records: {original_count})")

    return deduped_df


def process_scraped_data(data: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Complete processing pipeline for scraped business data.

    Steps:
    1. Convert to DataFrame
    2. Normalize values and schema
    3. Deduplicate records

    Args:
        data: List of raw business data dictionaries

    Returns:
        Processed and cleaned DataFrame
    """
    logger.info(f"Processing {len(data)} raw business records")

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Normalize
    df = normalize_dataframe(df)

    # Deduplicate
    df = deduplicate_dataframe(df)

    logger.info(f"Data processing complete: {len(df)} final records")
    return df
