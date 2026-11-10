import argparse
import csv
import calendar
import random
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# Supported insurance categories, regions, and claim statuses.
CLAIM_TYPES = ["Auto", "Home", "Health", "Travel"]

REGIONS = [
    "Ontario",
    "Quebec",
    "Alberta",
    "British Columbia",
    "Atlantic Canada"
]

STATUSES = ["OPEN", "APPROVED", "DENIED"]

# Define the CSV column names and their order.
# These match the data dictionary in our README.
FIELDS = [
    "claim_id",
    "policy_id",
    "claim_type",
    "region",
    "date_submitted",
    "date_closed",
    "status",
    "claimed_amount",
    "approved_amount",
    "last_updated_at"
]

"""
When we generate a record, it will contain these 10 fields.
For example, a single claim might look like:
{
    "claim_id": "CLM-0000001",
    "policy_id": "POL-000123",
    "claim_type": "Auto",
    "region": "Ontario",
    "date_submitted": "2026-01-05",
    "date_closed": "2026-01-18",
    "status": "APPROVED",
    "claimed_amount": "2500.00",
    "approved_amount": "2000.00",
    "last_updated_at": "2026-01-18T12:00:00"
}
"""

# Locate the project root directory.
# parents[0] = generation/
# parents[1] = src/
# parents[2] = azure-insurance-claims-pipeline/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Directory where generated CSV files will be stored.
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"


# ---------------------------------------------------------
# Claim generation
# ---------------------------------------------------------
def generate_claim(claim_number, month, rng):
    """
    Generate one synthetic (made-up but realistic) insurance claim.

    Args:
        claim_number: Unique sequential number for the claim.
        month: Month the claim was submitted (1-12).
        rng: Random number generator used to create values.

    Returns:
        A dictionary containing the generated claim.
    """

    # Find the last valid day of the selected month.
    # For example, January has 31 days and February 2026 has 28.
    last_day = calendar.monthrange(2026, month)[1]

    # Generate a random submission date within the month.
    submitted = date(
        2026,
        month,
        rng.randint(1, last_day)
    )

    # Randomly assign a claim status using weighted probabilities.
    # These percentages are fictional project assumptions.
    # OPEN: 20%, APPROVED: 65%, DENIED: 15%.
    status = rng.choices(
        STATUSES,
        weights=[20, 65, 15],
        k=1 # This tells Python to select one result
    )[0] # extract the first element since choices() returns a list

    # Generate a fictional claim between $100 and $20,000 CAD.
    # Generating an integer number of cents helps ensure that the original amount has precisely two decimal places.
    claimed_cents = rng.randint(10000, 2000000)

    # Convert cents to dollars.
    claimed = claimed_cents / 100

    # Determine the closure date and approved amount
    # based on the generated claim status.
    if status == "OPEN":

        # Open claims have not yet been resolved.
        closed = None
        approved = 0.0

    else:
        # For this first version, resolved claims close
        # within their original submission month.
        max_days = (
            date(2026, month, last_day) - submitted
        ).days

        # Choose how many days after submission the claim closes.
        days_to_close = rng.randint(0, max_days)

        closed = submitted + timedelta(days=days_to_close)

        if status == "APPROVED":
            # Approved claims receive 50%-100% of the
            # amount originally requested.
            approved = round(
                claimed * rng.uniform(0.5, 1.0),
                2
            )

        else:
            # Denied claims receive no approved amount.
            approved = 0.0
    
    # If closed contains a date, use that. Otherwise, use submitted.
    updated = closed or submitted

    # Return the generated claim as a dictionary.
    # Dictionary keys correspond to our CSV column names.
    return {
        "claim_id": f"CLM-{claim_number:07d}", # at least 7 digits
        "policy_id": f"POL-{rng.randint(1, 30000):06d}",
        "claim_type": rng.choice(CLAIM_TYPES),
        "region": rng.choice(REGIONS),
        "date_submitted": submitted.isoformat(), #Converts a Python date object into a string like "2026-01-15"
        "date_closed": closed.isoformat() if closed else "",
        "status": status,
        "claimed_amount": f"{claimed:.2f}",
        "approved_amount": f"{approved:.2f}",
        "last_updated_at": f"{updated.isoformat()}T12:00:00"
    }




# ---------------------------------------------------------
# Monthly CSV generation
# ---------------------------------------------------------
def main(total_claims, seed):
    """
    Generate synthetic claims and export 12 monthly CSV files.

    Args:
        total_claims: Total number of unique claims to generate.
        seed: Random seed for reproducible results.
    """

    # Use a dedicated seeded generator so identical inputs
    # produce identical synthetic data.
    rng = random.Random(seed)

    # Create the output directory if it does not exist.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Divide the total claims evenly across 12 months.
    # Any remainder is distributed across the earliest months.
    base, remainder = divmod(total_claims, 12)
    # divmod(a, b) returns the quotient and remainder of dividing a by b.

    # Start claim IDs at 1.
    claim_number = 1

    # Generate one CSV file for each month of 2026.
    for month in range(1, 13):
        # Give an additional claim to the first 'remainder' months.
        count = base + (1 if month <= remainder else 0)

        # Example: claims_2026_01.csv
        filename = (
            OUTPUT_DIR / f"claims_2026_{month:02d}.csv"
        )

        # Open the file and write the CSV header and records.
        with filename.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            # Create a CSV writer using our predefined columns.
            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS
            )

            # Write the column headers first.
            writer.writeheader()

            # Generate the assigned number of claims.
            for _ in range(count):
                claim = generate_claim(
                    claim_number,
                    month,
                    rng
                )

                # Write the claim dictionary as a CSV row.
                writer.writerow(claim)

                # Increment the ID so each claim is unique.
                claim_number += 1

        # Display progress after writing each monthly file.
        print(
            f"Created {filename.name}: {count:,} claims"
        )

    # Display the total number of generated claims.
    print(
        f"\nTotal unique claims: {claim_number - 1:,}" #:, formats large numbers with commas
        #We subtract 1 because claim_number is incremented after every generated claim.
    )


# ---------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------

if __name__ == "__main__":

    # Create a parser to accept command-line arguments.
    parser = argparse.ArgumentParser(
        description="Generate synthetic insurance claims CSV files."
    )

    # Number of unique insurance claims to generate.
    # Defaults to 1,000 when --count is not provided.
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Total number of unique claims to generate."
    )

    # Random seed used to produce reproducible datasets.
    # The same seed and claim count produce identical records.
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data generation."
    )

    # Read the command-line arguments.
    args = parser.parse_args()

    # Reject invalid claim counts.
    if args.count < 1:
        parser.error("--count must be a positive integer")

    # Run the generator using the supplied arguments.
    main(
        total_claims=args.count,
        seed=args.seed
    )