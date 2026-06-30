# Polytank Retail Audit

## Overview

The **Polytank Retail Audit** pipeline extracts retail audit data from the STG platform for the Polytank Retail Audit study. The pipeline retrieves completed interviews from the Recruitment survey, transforms the raw interview responses into structured datasets, and loads the processed data into a MySQL database for reporting and analysis.

The pipeline generates three analytical datasets covering retailer information, product details and product sales. Each dataset is processed independently and loaded into its corresponding database table.

---

# Directory Structure

```text
Polytank Retail Audit/
│
├── __init__.py
├── main_argparse.py
├── functions2.py
├── requirements.txt
├── credentials_2.json
└── README.md
```

| File                 | Description                                                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `main_argparse.py`   | Main execution script responsible for processing user input, coordinating data extraction and loading processed datasets into the database. |
| `functions2.py`      | Contains the data extraction, parsing and transformation routines for each dataset.                                                         |
| `credentials_2.json` | Stores STG authentication details, survey identifiers and MySQL connection settings.                                                        |
| `requirements.txt`   | Python package dependencies required by the pipeline.                                                                                       |
| `README.md`          | Project documentation.                                                                                                                      |

---

# Supported Extraction Types

The pipeline supports the following extraction modes.

| Extraction Type   | Description                                   | Database Table    |
| ----------------- | --------------------------------------------- | ----------------- |
| `recruit_profile` | Retailer profile and outlet information       | `recruit_profile` |
| `product_details` | Product inventory and product characteristics | `product_details` |
| `product_sales`   | Product sales and availability information    | `product_sales`   |

---

# Running the Pipeline

Execute the pipeline from the command line.

```bash
python main_argparse.py -f <file_type> -s <start_date> -e <end_date>
```

Example:

```bash
python main_argparse.py -f product_sales -s 2026-01-01 -e 2026-01-31
```

### Command Line Arguments

| Argument        | Description                        |
| --------------- | ---------------------------------- |
| `-f`, `--file`  | Extraction type to execute.        |
| `-s`, `--start` | Start date in `YYYY-MM-DD` format. |
| `-e`, `--end`   | End date in `YYYY-MM-DD` format.   |

---

# Outputs

Each extraction mode produces a dedicated dataset that is appended to its corresponding MySQL table.

| Dataset          | Destination Table |
| ---------------- | ----------------- |
| Retailer Profile | `recruit_profile` |
| Product Details  | `product_details` |
| Product Sales    | `product_sales`   |

Excel export statements remain in the source code for validation purposes but are currently disabled. The production pipeline writes all processed datasets directly to the configured MySQL database.

---

# Data Processing

For each date within the selected date range, the pipeline performs the following operations:

1. Retrieves completed interviews from the Recruitment survey.
2. Downloads interview responses from the STG platform.
3. Parses the XML interview data.
4. Extracts variables required for the selected dataset.
5. Cleans and standardises the extracted data.
6. Combines all processed interviews into a single dataset.
7. Adds the reporting period to each record.
8. Loads the processed data into the corresponding MySQL table.

Each extraction type applies its own transformation routine based on the survey questionnaire and reporting requirements.

---

# Configuration

Before executing the pipeline, update `credentials_2.json` with the appropriate values for:

* STG username
* STG password
* Recruitment Survey ID
* MySQL username
* MySQL password
* Destination database
* Database host
* Database port

Ensure that the Recruitment Survey ID corresponds to the active fieldwork before running the pipeline.

---

# Known Improvements

The STG API key is currently hard-coded within `main_argparse.py`.

As part of a future enhancement, the API key should be moved into `credentials_2.json` so that all configuration settings are maintained in a single location. This change should be implemented only after it has been validated in a test environment.

---

# Maintenance

Before each reporting cycle:

1. Verify that the Recruitment Survey ID is current.
2. Confirm STG credentials remain valid.
3. Verify the MySQL connection details.
4. Review any questionnaire updates that may require modifications to the transformation routines.
5. Execute each extraction mode to verify successful data extraction before loading production data.
