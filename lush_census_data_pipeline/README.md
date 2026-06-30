# Lush Census Data Pipeline

## Overview

The **Lush Census Data Pipeline** extracts census data collected through the STG platform for the Lush retail and salon census study. The pipeline downloads completed interviews, transforms the XML responses into structured analytical datasets, and loads the processed outputs into a MySQL database.

The project captures information describing participating outlets, their geographic locations, product categories, supply sources, and business structure. Several datasets require additional transformation to normalize multiple-response survey questions into analysis-ready tables.

---

# Directory Structure

```text
Lush Census Data Pipeline/
│
├── __init__.py
├── main_argparse.py
├── functions2.py
├── requirements.txt
├── credentials_2.json
└── README.md
```

| File                 | Description                                                                                                                   |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `main_argparse.py`   | Entry point for the pipeline. Handles command-line arguments, orchestrates downloads and loads processed datasets into MySQL. |
| `functions2.py`      | Contains STG API communication, XML parsing and all dataset transformation routines.                                          |
| `credentials_2.json` | Stores STG credentials, survey identifiers and MySQL connection settings.                                                     |
| `requirements.txt`   | Python dependencies required by the project.                                                                                  |
| `README.md`          | Project documentation.                                                                                                        |

---

# Supported Extraction Types

The pipeline supports the following datasets.

| Extraction Type   | Description                                                                | Database Table           |
| ----------------- | -------------------------------------------------------------------------- | ------------------------ |
| `recruit_profile` | Outlet profile and interview information                                   | `new_recruit_profile`    |
| `location`        | Outlet GPS coordinates and location information                            | `recruit_location`       |
| `supply_source`   | Primary supplier information for each outlet                               | `supply_source`          |
| `extra_category`  | Additional cosmetic and body care product categories stocked by the outlet | `recruit_extra_category` |
| `outlet_type`     | Business structure classification (Salon/Retail)                           | `recruit_outlet_type`    |
| `category`        | Hair care product categories and associated wet/dry product segments       | `recruit_category`       |

---

# Running the Pipeline

Execute the pipeline from the command line.

```bash
python main_argparse.py -f <file_type> -s <start_date> -e <end_date>
```

Example:

```bash
python main_argparse.py -f category -s 2024-01-01 -e 2024-01-31
```

### Command Line Arguments

| Argument        | Description                        |
| --------------- | ---------------------------------- |
| `-f`, `--file`  | Dataset to extract.                |
| `-s`, `--start` | Start date in `YYYY-MM-DD` format. |
| `-e`, `--end`   | End date in `YYYY-MM-DD` format.   |

---

# Outputs

Each extraction mode generates a dedicated dataset and appends the processed records to its corresponding MySQL table.

| Dataset               | Destination Table        |
| --------------------- | ------------------------ |
| Recruitment Profile   | `new_recruit_profile`    |
| Recruitment Location  | `recruit_location`       |
| Supply Source         | `supply_source`          |
| Additional Categories | `recruit_extra_category` |
| Outlet Type           | `recruit_outlet_type`    |
| Hair Categories       | `recruit_category`       |

Excel export statements remain available within the source code for validation purposes but are disabled in the production workflow. Production data is written directly to MySQL.

---

# Data Processing

For each date within the selected reporting period, the pipeline performs the following operations:

1. Retrieves completed interview IDs from the STG platform.
2. Downloads XML interview responses.
3. Parses the XML structure into tabular data.
4. Extracts variables required for the selected dataset.
5. Cleans and standardises extracted values.
6. Applies dataset-specific transformation rules.
7. Adds the reporting period to each record.
8. Loads the processed dataset into the corresponding MySQL table.

---

# Dataset-Specific Transformations

Some datasets include additional processing to improve analytical usability.

### Recruitment Location

* Extracts GPS information captured during fieldwork.
* Separates GPS coordinates into:

  * Latitude
  * Longitude
  * Capture timestamp
  * Altitude
  * Bearing
  * Speed

### Additional Categories

* Multiple-response product categories are split into individual records.
* Each selected category becomes its own row, simplifying aggregation and reporting.

### Hair Categories

* Handles multiple selections across hair product categories.
* Expands combined responses into individual category records.
* Separates Wet Hair and Dry Hair product segments while preserving the relationship between category and segment.
* Removes empty category-segment combinations before loading.

### Outlet Type

* Extracts outlet classification information, including Salon and Retail structures.

---

# Configuration

Before running the pipeline, update `credentials_2.json` with:

* STG username
* STG password
* Recruitment Survey ID
* MySQL username
* MySQL password
* Database host
* Database name
* Database port

Verify that the Recruitment Survey ID corresponds to the active fieldwork before executing the pipeline.

---

# Known Improvements

The STG API key is currently hard-coded within `main_argparse.py`.

As part of a future enhancement, the API key should be moved into `credentials_2.json` so that all configuration settings are maintained in a single location. This change should be implemented after appropriate testing.

---

# Maintenance

Before each reporting cycle:

1. Verify that the Recruitment Survey ID is current.
2. Confirm STG credentials are valid.
3. Test the MySQL database connection.
4. Review any questionnaire updates that may require changes to the transformation logic.
5. Execute each extraction mode to verify successful data extraction before loading production data.
