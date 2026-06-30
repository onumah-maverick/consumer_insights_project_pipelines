# Togo Water Data Extraction Pipeline

## Overview

The **Togo Water Data Extraction Pipeline** is a project-specific implementation of the shared STG Data Extraction Framework. It extracts Audit Capture and Recruitment survey data from the STG platform, transforms the raw interview responses into structured datasets, and loads the processed data into a MySQL database for reporting and analysis.

This project supports multiple extraction modes covering outlet profiles, product listings and supplier information. Refer to the repository README for details on the common framework architecture and setup.

---

# Project Structure

```text
Togo Water/
│
├── __init__.py
├── main_argparse.py
├── functions.py
├── requirements.txt
├── credentials.json
└── README.md
```

| File               | Description                                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `main_argparse.py` | Entry point for the pipeline. Reads configuration, accepts user arguments and orchestrates the extraction process. |
| `functions.py`     | Contains all download, parsing and project-specific transformation logic.                                          |
| `credentials.json` | Stores STG and MySQL connection details together with the project Survey IDs.                                      |
| `requirements.txt` | Python package dependencies.                                                                                       |
| `README.md`        | Project documentation.                                                                                             |

---

# Supported Extraction Types

The pipeline supports the following extraction modes.

| Command            | Description                  | Output Table            |
| ------------------ | ---------------------------- | ----------------------- |
| `audit_profile`    | Audit Capture outlet profile | `audit_capture_profile` |
| `new_items`        | Newly listed products        | `new_items`             |
| `old_items`        | Existing products            | `old_items`             |
| `recruit_profile`  | Recruitment outlet profile   | `recruitment_profile`   |
| `recruit_items`    | Recruitment product listings | `recruitment_items`     |
| `supplier_profile` | Supplier profile information | `supplier_profile`      |

---

# Running the Pipeline

The pipeline is executed from the command line.

```bash
python main_argparse.py -f <file_type> -s <start_date> -e <end_date>
```

Example:

```bash
python main_argparse.py -f audit_profile -s 2026-01-01 -e 2026-01-07
```

### Parameters

| Argument        | Description                        |
| --------------- | ---------------------------------- |
| `-f`, `--file`  | Extraction type to execute.        |
| `-s`, `--start` | Start date in `YYYY-MM-DD` format. |
| `-e`, `--end`   | End date in `YYYY-MM-DD` format.   |

---

# Output

Depending on the selected extraction mode, the pipeline produces one or both of the following outputs.

## Excel

The following extraction modes generate Excel files:

* Audit Capture Profile
* New Items
* Old Items

Output files follow the naming convention:

```text
audit_capture_profile_<start>_<end>.xlsx
new_items_<start>_<end>.xlsx
old_items_<start>_<end>.xlsx
```

## MySQL

Processed records are appended to the following database tables:

* audit_capture_profile
* new_items
* old_items
* recruitment_profile
* recruitment_items
* supplier_profile

---

# Project-Specific Processing

The Togo Water pipeline includes transformation routines for both Audit Capture and Recruitment surveys.

The transformation layer performs tasks including:

* Parsing XML interview responses.
* Extracting required survey variables.
* Standardising field names.
* Formatting dates and timestamps.
* Parsing GPS coordinates into separate fields where applicable.
* Combining all processed interviews into a single dataset for each extraction type.
* Appending a reporting period to each record before export.

The exact transformation logic is implemented within `functions.py`.

---

# Configuration

Before running the pipeline, update `credentials.json` with:

* STG username
* STG password
* Audit Capture Survey ID
* Recruitment Survey ID
* MySQL connection details

These values are project-specific and should be reviewed whenever a new survey is deployed.

---

# Known Limitations

The STG API key is currently defined within `main_argparse.py` as a hard-coded value.

A future enhancement is to relocate the API key into `credentials.json` so that all configuration values are maintained in a single location. This change has been identified but has not yet been implemented, as it should be validated before deployment to avoid disrupting the production pipeline.

---

# Maintenance Notes

When preparing for a new fieldwork cycle:

1. Verify the Audit Capture and Recruitment Survey IDs.
2. Confirm STG credentials remain valid.
3. Confirm MySQL connection details.
4. Review any survey changes that may require updates to the transformation logic.
5. Execute each extraction mode to verify successful data retrieval before production use.
