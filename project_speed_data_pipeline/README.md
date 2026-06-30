# Project Speed for Boxer Motorbike

## Overview

The **Project Speed for Boxer Motorbike** pipeline extracts consumer survey data from the STG platform for the Project Speed study. The pipeline retrieves completed interviews from the Recruitment survey, transforms the raw XML responses into structured analytical datasets, and loads the processed data into a MySQL database for reporting and analysis.

The pipeline generates datasets covering respondent demographics, media consumption, advertisement effectiveness, advertisement impressions, brand awareness, brand perceptions and brand associations. Each dataset is processed independently and loaded into its corresponding database table.

---

# Directory Structure

```text
Project Speed for Boxer Motorbike/
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

| Extraction Type     | Description                                          | Database Table      |
| ------------------- | ---------------------------------------------------- | ------------------- |
| `recruit_profile`   | Respondent demographic and profile information       | `recruit_profile`   |
| `media`             | Media consumption and social media usage             | `media`             |
| `advert`            | Advertisement recall and advertisement evaluation    | `advert`            |
| `advert_impression` | Consumer impressions of advertising campaigns        | `advert_impression` |
| `brand_aware`       | Brand awareness responses                            | `brand_awareness`   |
| `brand_description` | Consumer descriptions and perceptions of brands      | `brand_description` |
| `brand_association` | Brand association attributes selected by respondents | `brand_association` |

---

# Running the Pipeline

Execute the pipeline from the command line.

```bash
python main_argparse.py -f <file_type> -s <start_date> -e <end_date>
```

Example:

```bash
python main_argparse.py -f brand_aware -s 2025-12-30 -e 2025-12-31
```

### Command Line Arguments

| Argument        | Description                        |
| --------------- | ---------------------------------- |
| `-f`, `--file`  | Extraction type to execute.        |
| `-s`, `--start` | Start date in `YYYY-MM-DD` format. |
| `-e`, `--end`   | End date in `YYYY-MM-DD` format.   |

---

# Outputs

Each extraction mode produces a dedicated analytical dataset that is appended to its corresponding MySQL table.

| Dataset                   | Destination Table   |
| ------------------------- | ------------------- |
| Recruitment Profile       | `recruit_profile`   |
| Media Consumption         | `media`             |
| Advertisement Evaluation  | `advert`            |
| Advertisement Impressions | `advert_impression` |
| Brand Awareness           | `brand_awareness`   |
| Brand Description         | `brand_description` |
| Brand Association         | `brand_association` |

Excel export statements remain in the source code for development and validation purposes but are currently disabled. The production pipeline loads all processed datasets directly into MySQL.

---

# Data Processing

The pipeline retrieves completed interviews for the selected date range and transforms the raw survey responses into structured datasets suitable for analysis.

Processing includes:

* Retrieving interview data from the STG platform.
* Parsing XML interview responses.
* Extracting variables required for each analytical dataset.
* Standardising and formatting response values.
* Combining individual interview records into a single dataset.
* Adding reporting period information where applicable.
* Loading the processed data into the corresponding MySQL table.

Each extraction type applies its own transformation routine based on the survey structure and reporting requirements.

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

Ensure that the Recruitment Survey ID corresponds to the active survey before running the extraction.

---

# Known Improvements

The STG API key is currently defined within `main_argparse.py`.

As part of a future enhancement, the API key should be moved into `credentials_2.json` so that all application configuration is maintained in a single location. This change has been identified but has not yet been implemented, as it should be validated before deployment to avoid disrupting the production pipeline.

---

# Maintenance

Before each reporting cycle:

1. Verify that the Recruitment Survey ID is current.
2. Confirm STG credentials remain valid.
3. Verify the MySQL connection details.
4. Review any questionnaire updates that may require changes to the transformation routines.
5. Execute each extraction mode to confirm successful data retrieval before loading production data.
