import argparse
import csv
import random
from pathlib import Path

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
    with file_path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

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

def inject_duplicates(claims, rng, duplicate_rate=0.05):
    """
    Add exact duplicate records to a claims dataset.

    Args:
        claims: List of original claim dictionaries.
        rng: Shared random number generator.
        duplicate_rate: Percentage of records to duplicate.

    Returns:
        List containing original records and duplicates.
    """

    # Calculate the number of duplicates to introduce. 5% for now
    duplicate_count = round(len(claims) * duplicate_rate)

    # Randomly select records to duplicate.
    # sample() selects without replacement.
    # Selecting 5% of claims randomly to duplicate
    selected = rng.sample(claims, duplicate_count)

    # claim.copy() Creates a separate dictionary containing the same field values.
    # copy the claim in selected as a list and store in duplicates
    duplicates = []
    for claim in selected:
        duplicates.append(claim.copy())

    # Combine original records with the duplicates.
    corrupted_claims = claims + duplicates

    return corrupted_claims


# ---------------------------------------------------------
# Temporary test: Copy clean claims to test directory
# ---------------------------------------------------------

if __name__ == "__main__":

    # Create one reproducible random generator for all files.
    rng = random.Random(42)

    # Find the clean monthly CSV files.
    files = sorted(INPUT_DIR.glob("claims_2026_??.csv"))

    # Stop if no source files were found.
    if not files:
        raise FileNotFoundError(f"No monthly CSV files found in {INPUT_DIR}")

    # Process each monthly CSV file.
    for file_path in files:

        # Read the original column names and claims.
        fieldnames, claims = read_claims(file_path)

        # Inject duplicates into the current monthly dataset.
        # The original clean CSV remains unchanged.
        corrupted_claims = inject_duplicates(
            claims,
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

        # Display original and duplicate record counts.
        duplicate_count = len(corrupted_claims) - len(claims)

        print(
            f"Copied {file_path.name}: "
            f"{len(claims):,} original records, "
            f"{duplicate_count:,} duplicates"
        )
