# STG Data Extraction Pipelines

## Overview

This repository contains a collection of Python-based ETL (Extract, Transform, Load) pipelines developed to retrieve survey data from the **STG (Dooblo)** platform for various Consumer Insights projects.

Although each project targets a different survey and client, all pipelines follow the same core architecture:

1. Connect to the STG API.
2. Retrieve survey interview (Subject) IDs for a specified date range.
3. Download interview responses in XML format.
4. Transform raw XML into structured tabular datasets.
5. Clean and standardize extracted variables.
6. Export processed data to Excel (where applicable).
7. Load the processed datasets into a MySQL database.

This shared architecture allows new projects to be developed by extending the transformation logic while reusing the same extraction framework.

---

# Repository Structure

```text
Repository/
│
├── Project 1/
│   ├── __init__.py
│   ├── main_argparse.py
│   ├── functions.py
│   ├── requirements.txt
│   ├── credentials.json
│   └── README.md
│
├── Project 2/
│   └── ...
│
├── Project 3/
│   └── ...
│
└── README.md
```

Each project is self-contained and includes its own configuration, transformation logic and project-specific documentation.

---

# Pipeline Architecture

Every project follows the same processing workflow.

```text
                    STG Platform
                         │
                         ▼
               Authenticate with API
                         │
                         ▼
          Retrieve Subject IDs by Date Range
                         │
                         ▼
        Download Interview XML for Each Subject
                         │
                         ▼
              Parse XML into Structured Data
                         │
                         ▼
          Apply Project-specific Transformations
                         │
                         ▼
           Merge Daily Extraction Results
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Export Excel          Load into MySQL
```

The transformation layer differs between projects while the download and processing framework remains largely unchanged.

---

# Common Project Structure

Most projects consist of the following files.

| File               | Purpose                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------- |
| `main_argparse.py` | Main execution script. Parses command-line arguments and orchestrates the ETL workflow. |
| `functions.py`     | Contains the download, parsing and transformation logic.                                |
| `credentials.json` | Stores project configuration and database credentials.                                  |
| `requirements.txt` | Python package dependencies.                                                            |
| `README.md`        | Project-specific documentation.                                                         |
| `__init__.py`      | Python package initialization.                                                          |

---

# Core Components

## Extraction Layer

The `DownloadDetails` class is responsible for communication with the STG API.

Primary responsibilities include:

* Authenticating API requests.
* Retrieving Subject IDs for a specified survey and date.
* Downloading XML interview responses.
* Parsing XML into a structured format for downstream processing.

---

## Transformation Layer

Project-specific transformation classes convert XML responses into normalized pandas DataFrames.

Typical processing includes:

* Selecting required survey variables.
* Cleaning and standardizing responses.
* Renaming fields.
* Formatting dates.
* Parsing GPS coordinates.
* Removing unwanted records.
* Combining related survey sections into a single dataset.

Each project implements only the transformations required for its own survey structure.

---

## Loading Layer

The loading layer is managed by `main_argparse.py`.

Responsibilities include:

* Reading project configuration.
* Parsing user input.
* Processing the requested date range.
* Combining transformed datasets.
* Exporting Excel outputs where required.
* Appending processed data to MySQL tables.

---

# Installation

Install all required Python packages before executing any project.

```bash
pip install -r requirements.txt
```

Each project maintains its own `requirements.txt` file to ensure dependency isolation.

---

# Configuration

Project configuration is stored in `credentials.json`.

Typical configuration includes:

```json
{
    "username": "",
    "password": "",
    "recruitment_survey": "",
    "audit_survey": "",
    "sql_user": "",
    "sql_password": "",
    "sql_database": "",
    "host": "localhost",
    "port": "3306"
}
```

Configuration fields include:

| Parameter          | Description               |
| ------------------ | ------------------------- |
| username           | STG username              |
| password           | STG password              |
| recruitment_survey | Recruitment survey UUID   |
| audit_survey       | Audit Capture survey UUID |
| sql_user           | MySQL username            |
| sql_password       | MySQL password            |
| sql_database       | Destination database      |
| host               | MySQL server              |
| port               | MySQL server port         |

Survey identifiers differ between projects and should be updated accordingly.

---

# Running a Pipeline

All pipelines are executed through the command line using the same interface.

```bash
python main_argparse.py -f <file_type> -s <start_date> -e <end_date>
```

Example:

```bash
python main_argparse.py -f audit_profile -s 2026-01-01 -e 2026-01-07
```

Dates must follow the ISO format:

```text
YYYY-MM-DD
```

Refer to each project's README for the available extraction types.

---

# Creating a New Pipeline

Most new projects can be created by copying an existing project folder and updating:

* Survey UUIDs.
* Transformation methods in `functions.py`.
* Output filenames.
* Destination database tables.
* Project documentation.

Because the API interaction layer is shared, new development is typically limited to the transformation logic.

---

# Project Documentation

Each project folder contains its own README describing:

* Project purpose.
* Survey configuration.
* Supported extraction types.
* Output datasets.
* Database tables.
* Project-specific processing rules.

This repository README documents the common framework shared by all projects.

---

# Known Improvements

The framework is functional and actively used in production; however, several enhancements have been identified to improve maintainability.

### Move API Key into Configuration

The STG API key is currently defined within `main_argparse.py`.

A future enhancement is to move this value into `credentials.json`, allowing all configuration to be maintained in a single location without modifying source code.

This change has not yet been implemented to avoid disrupting existing production pipelines before validation.

### Logging

Replace console `print()` statements with Python's `logging` module to provide configurable log levels and persistent execution logs.

### Configuration Validation

Add validation checks to confirm required configuration values are present before execution begins.

### Retry Mechanism

Introduce retry logic for transient network or API failures to improve pipeline resilience.

### Unit Testing

Add automated tests for XML parsing and transformation functions to simplify maintenance and reduce regression risk.

---

# Maintenance Notes

When onboarding a new project or beginning a new fieldwork cycle:

1. Verify the survey UUIDs.
2. Update project credentials if required.
3. Confirm database connection details.
4. Review any survey changes that may require updates to the transformation logic.
5. Test each extraction mode before production execution.

---

# Contributing

When extending the repository:

* Reuse the existing download framework wherever possible.
* Keep transformation logic isolated within project-specific classes.
* Document any new extraction types in the corresponding project README.
* Maintain consistent naming conventions across projects to simplify long-term maintenance.

