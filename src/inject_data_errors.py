import argparse
import csv
import random
from pathlib import Path
from datetime import date, timedelta
import json

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# Locate the repository root from the src/ directory.
# parents[0] = src/
# parents[1] = project root/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Input directory containing valid monthly claims.
INPUT_DIR = PROJECT_ROOT / "data" / "clean"

# Output directory for intentionally corrupted datasets.
OUTPUT_DIR = PROJECT_ROOT / "data" / "test"

# ---------------------------------------------------------
# CSV reading
# ---------------------------------------------------------

def read_claims(file_path):
    """
    Read a CSV file containing insurance claims.

    Args:
        file_path: Path to the input CSV file.

    Returns:
        A tuple containing the column names and claim records.
    """

    # Open the CSV file for reading.
    with file_path.open("r",newline="",encoding="utf-8") as file:

        # creates a reader ready to read the CSV
        reader = csv.DictReader(file)

        """
        csv.DictReader converts each row into a dictionary:
        {
            "claim_id": "CLM-0000001",
            "status": "OPEN",
            "claimed_amount": "1500.00"
        }
        """

        # reads the header and stores it in fieldnames
        fieldnames = reader.fieldnames

        # reads all the data rows and stores them in claims
        claims = list(reader)

    return fieldnames, claims


# ---------------------------------------------------------
# CSV writing
# ---------------------------------------------------------

def write_claims(file_path, fieldnames, claims):
    """
    Write insurance claim records to a CSV file,
    sorted by claim_id in ascending order.

    Args:
        file_path: Destination CSV file.
        fieldnames: Column names and their order.
        claims: List of claim dictionaries.
    """

    # Create the output directory if it doesn't exist.
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Sort records by claim_id before writing.
    claims = sorted(claims,key=lambda claim: claim["claim_id"])

    # Write the data to the destination CSV file.
    with file_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        # Write the column headers.
        writer.writeheader()

        # Write every claim record.
        writer.writerows(claims)

# ---------------------------------------------------------
# Duplicate record injection
# ---------------------------------------------------------

def inject_duplicates(claims, rng, duplicate_rate):
    """
    Add exact duplicate records to a claims dataset.

    Args:
        claims: List of original claim dictionaries.
        rng: Shared random number generator.
        duplicate_rate: Percentage of records to duplicate.

    Returns:
        A tuple containing:
        - Original records plus duplicates
        - Details of the duplicated records
    """

    # Calculate the number of duplicates to introduce. 5% for now
    duplicate_count = round(len(claims) * duplicate_rate)

    # sample() selects without replacement.
    # Selecting 5% of claims randomly to duplicate
    # Select row indices to duplicate.
    selected_indices = rng.sample(range(len(claims)),duplicate_count)

    # claim.copy() Creates a separate dictionary containing the same field values.
    # copy the claim in selected as a list and store in duplicates
    duplicates = []
    duplicate_details = []

    for row_index in selected_indices:

        # Get the record being duplicated.
        original = claims[row_index]

        # Create an independent copy of the record.
        duplicates.append(original.copy())

        # Track which original row was duplicated.
        duplicate_details.append({
            "source_row_index": row_index,
            "claim_id": original["claim_id"]
        })

    # Combine original records with the duplicates.
    duplicated_claims = claims + duplicates

    return duplicated_claims, duplicate_details

# ---------------------------------------------------------
# Invalid record injection
# ---------------------------------------------------------
def inject_invalid_records(claims, rng, error_rate):
    """
    Introduce intentional data quality errors such as
    missing claim id,
    invalid status,
    negative amount,
    invalid date,
    invalid chronology,
    excessive approval

    Args:
        claims: List of claim dictionaries.
        rng: Shared random number generator.
        error_rate: Fraction of records to corrupt.

    Returns:
        Returns modified records, summary counts, and individual errors.
    """

    # Create independent copies to protect the original records.
    corrupted_claims = []
    for claim in claims:
        corrupted_claims.append(claim.copy())

    # Calculate how many records should contain errors. 10% for now
    error_count = round(len(corrupted_claims) * error_rate)

    # Select random row indices rather than claim dictionaries.
    # This lets us identify exactly which CSV rows were modified.
    selected_indices = rng.sample(range(len(corrupted_claims)),error_count)

    # Store information about each intentionally corrupted record.
    injected_errors = []

    # Available error scenarios.
    error_types = [
        "missing_id",
        "invalid_status",
        "negative_amount",
        "invalid_date",
        "invalid_chronology",
        "excessive_approval"
    ]

    # Track how many times each error type is injected.
    # Initialize every count to zero.
    error_counts = {}
    for error_type in error_types:
        error_counts[error_type] = 0

    # Calculate how many errors of each type to generate.
    # divmod() gives us the base count and any remainder.
    # 10% of errors divided by 6 error types
    # lets say 10 records to be invalid, base = 1, remainder = 4
    # Each error type happening at least once (base) 4 random ones will get 2
    base, remainder = divmod(error_count, len(error_types))

    # Create a list containing an approximately equal
    # number of occurrences of each error type.
    assigned_errors = []

    # Randomly select which error types receive one extra error.
    # sample() selects without replacement.
    extra_types = rng.sample(error_types, remainder)

    for error_type in error_types:
        # Give each type its base count and one extra if randomly selected.
        count = base + (1 if error_type in extra_types else 0)

        # [error_type] * count creates a list. 
        # extend() adds each item from that list,
        # append() would've added the whole list as one item.
        assigned_errors.extend([error_type] * count)

    # Shuffle assignments so errors occur in random order.
    rng.shuffle(assigned_errors)

    # Pair selected row positions with their assigned error types.
    for row_index, error_type in zip(selected_indices, assigned_errors):

        # Access the record we're going to corrupt.
        claim = corrupted_claims[row_index]

        # Save the original claim ID before modifying anything.
        original_claim_id = claim["claim_id"]

        # Record which claim was modified and why.
        injected_errors.append({
            "row_index": row_index,
            "original_claim_id": original_claim_id,
            "error_type": error_type
        })

        # Record which error type we're introducing.
        error_counts[error_type] += 1

        if error_type == "missing_id":

            # Remove the claim's business identifier.
            claim["claim_id"] = ""

        elif error_type == "invalid_status":

            # Introduce an unsupported status.
            claim["status"] = "UNKNOWN"

        elif error_type == "negative_amount":

            # Claimed amounts cannot be negative.
            claim["claimed_amount"] = "-500.00"

        elif error_type == "invalid_date":

            # February 30 is not a valid calendar date.
            claim["date_submitted"] = "2026-02-30"

        elif error_type == "invalid_chronology":

            # Convert the submission date string into a date object.
            submitted = date.fromisoformat(claim["date_submitted"])

            # Set the closure date 1-10 days before submission.
            days_before = rng.randint(1, 10)
            invalid_closed = submitted - timedelta(days=days_before)

            # Introduce the invalid chronology.
            claim["date_closed"] = invalid_closed.isoformat()

        elif error_type == "excessive_approval":

            # Set the claim to APPROVED so the amount
            # comparison is meaningful.
            claim["status"] = "APPROVED"

            # Ensure the claim has a valid closure date.
            claim["date_closed"] = claim["date_submitted"]

            # Approved amounts cannot exceed claimed amounts.
            claimed = float(claim["claimed_amount"])
            claim["approved_amount"] = f"{claimed + 1000:.2f}"

    # Return modified records, summary counts, and individual errors.
    return corrupted_claims, error_counts, injected_errors

# ---------------------------------------------------------
# Temporary test: Copy clean claims to test directory
# ---------------------------------------------------------

if __name__ == "__main__":

    # Create one reproducible random generator for all files.
    rng = random.Random(42)

    # Store expected results for every monthly file.
    # We'll use this later to verify Databricks processing.
    results = {
        "seed": 42,
        "error_rate": 0.10,
        "duplicate_rate": 0.05,
        # The months dictionary will hold the results for each CSV file.
        "months": {} ,

        # Will hold each metric across all months
        "totals": {"original_records": 0,
                   "invalid_records_injected": 0,
                   "duplicate_rows_added": 0,
                   "total_test_records": 0
                   } 
    }

    # Find the clean monthly CSV files.
    files = sorted(INPUT_DIR.glob("claims_2026_??.csv"))

    # Stop if no source files were found.
    if not files:
        raise FileNotFoundError(f"No monthly CSV files found in {INPUT_DIR}")

    # Process each monthly CSV file.
    for file_path in files:

        # Read the original column names and claims.
        fieldnames, claims = read_claims(file_path)

        # Introduce invalid values into approximately 10%
        # of the original monthly claim records.
        # Generate invalid records and capture detailed error information.
        invalid_claims, error_counts, injected_errors = inject_invalid_records(
            claims,
            rng,
            error_rate=0.10
        )

        # Inject exact duplicates after corrupting selected rows.
        # Duplicates may therefore include invalid records.
        # Generate duplicates and record their source rows.
        corrupted_claims, duplicate_details = inject_duplicates(
            invalid_claims,
            rng,
            duplicate_rate=0.05
        )

        # Write a separate copy to the test directory.
        output_path = OUTPUT_DIR / file_path.name

        write_claims(
            output_path,
            fieldnames,
            corrupted_claims
        )

        # Count intentionally modified source records.
        # sum(error_counts.values()) adds up all six error type counts.
        invalid_count = sum(error_counts.values())

        # Display original and duplicate record counts.
        duplicate_count = len(corrupted_claims) - len(invalid_claims)

        # Extract the month from the filename.
        # Example: claims_2026_01.csv -> 2026-01
        # file_path.stem drops the .csv extension
        # .replace("claims_", "") removes "claims_"
        # .replace("_", "-") swaps the remaining underscore for a hyphen
        month_key = file_path.stem.replace("claims_", "").replace("_", "-")

        # Save this month's expected results.
        results["months"][month_key] = {
            "original_records": len(claims),
            "invalid_records_injected": invalid_count,
            "duplicate_rows_added": duplicate_count,
            "total_test_records": len(corrupted_claims),
            "error_types": error_counts.copy(),
            # Store details of every intentionally modified source record.
            "invalid_record_details": injected_errors,
            "duplicate_record_details": duplicate_details
        }

        print(
            f"Copied {file_path.name}: "
            f"{len(claims):,} original records, "
            f"{invalid_count:,} intentionally invalid, "
            f"{duplicate_count:,} duplicates"
        )

        for error_type, count in error_counts.items():
            print(f"  {error_type}: {count}")

    for month in results["months"].values():
        results["totals"]["original_records"] += month["original_records"]
        results["totals"]["invalid_records_injected"] += month["invalid_records_injected"]
        results["totals"]["duplicate_rows_added"] += month["duplicate_rows_added"]
        results["totals"]["total_test_records"] += month["total_test_records"]

    # -----------------------------------------------------
    # Export expected results to JSON
    # -----------------------------------------------------

    # Store the manifest beside our generated test CSV files.
    manifest_path = OUTPUT_DIR / "expected_results.json"

    # Write the results as JSON with four-space indentation.
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print(f"\nExpected results saved to: {manifest_path}")

