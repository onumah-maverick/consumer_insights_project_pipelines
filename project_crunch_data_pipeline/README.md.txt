# Nutrifoods Brand Health Tracking

### Automated STG Survey Data Extraction and ETL Pipeline

---

## Overview

The **Nutrifoods Brand Health Tracking** project is an automated ETL pipeline developed to retrieve respondent survey data from the STG data collection platform, transform it into structured analytical datasets, and load the processed results into a MySQL database.

The project was designed to eliminate repetitive manual downloads while creating clean, analysis-ready tables for continuous brand health monitoring. Individual survey modules are processed independently, allowing each section of the questionnaire to be refreshed without affecting the others.

Unlike a monolithic survey export, the pipeline separates each survey component into its own transformation workflow, making maintenance, troubleshooting, and downstream reporting considerably simpler.

---

## Objectives

The project was developed to:

* Automate extraction of completed survey responses from the STG platform.
* Convert nested API responses into structured relational datasets.
* Standardize respondent information across survey modules.
* Load cleaned datasets directly into MySQL.
* Support incremental data refreshes using configurable date ranges.
* Produce reporting-friendly datasets that simplify Excel-based analysis.

---

# System Architecture

```
                STG Survey Platform
                        │
                        │ API Authentication
                        ▼
            Download Respondent IDs
                        │
                        ▼
             Download Individual Surveys
                        │
                        ▼
         Module-Specific Transformations
                        │
                        ▼
           Clean Analytical DataFrames
                        │
                        ▼
              MySQL Database Tables
                        │
                        ▼
        Excel Analysis & Pivot Reporting
```

---

# Project Components

## 1. Survey Download Engine

The project authenticates against the STG platform using stored credentials before downloading respondent information.

Each execution begins by:

* loading API credentials
* authenticating with STG
* identifying respondents within the requested date range
* downloading survey responses for each respondent individually

Downloading respondent IDs first significantly reduces unnecessary API calls by ensuring only completed interviews are processed.

---

## 2. Argument-Based Execution

The pipeline is driven through a command-line interface, allowing analysts to request specific survey sections without modifying the source code.

Example:

```bash
python main_argparse.py -f recruit_profile -s 2026-01-01 -e 2026-01-31
```

Supported survey modules include:

| Parameter       | Description                           |
| --------------- | ------------------------------------- |
| recruit_profile | Respondent profile information        |
| tank_social     | Social and household overview         |
| brand_aware     | Brand awareness responses             |
| brand_impress   | Brand perception and impressions      |
| media           | Media habits                          |
| tank_preference | Brand preference and purchase reasons |

Each module executes its own transformation routine before loading results into the appropriate database table.

---

# Survey Transformation Modules

Each survey section has a dedicated transformation function responsible for converting raw STG JSON responses into structured tabular data.

## Recruitment Profile

Processes demographic and respondent profile information including identifiers and background characteristics.

Output table:

```
recruit_profile
```

---

## Social Profile

Transforms respondent household and lifestyle information into an analytical format.

Output table:

```
owner_overview
```

---

## Brand Awareness

Processes all brand awareness questions captured within the survey.

Rather than mixing awareness information with unrelated survey responses, the module produces a dedicated awareness dataset suitable for downstream reporting.

Output table:

```
brand_awareness
```

---

## Brand Impression

Processes respondent perceptions and evaluations of different brands.

Output table:

```
owner_impression
```

---

## Media Habits

Transforms media consumption behaviour into a structured dataset for communication planning and audience profiling.

Output table:

```
media
```

---

## Brand Preference

Processes favourite brands together with the reasons behind respondent preference.

Output table:

```
tank_preferences
```

---

# Brand Awareness Expansion

One of the more significant reporting improvements within the project was the introduction of the **Brand Awareness Expansion** process.

Initially, all awareness variables existed together inside a single wide table containing numerous awareness columns.

While suitable for storage, this structure proved difficult to analyse using Excel Pivot Tables because:

* the dataset became unnecessarily wide
* pivot tables became increasingly complex
* distinct respondent counts required referencing many separate awareness columns
* refresh performance degraded as additional awareness measures were introduced

To simplify reporting, a separate transformation was created that reshaped the awareness data into a reporting-friendly structure.

Instead of storing awareness as many independent columns, the expansion converts awareness responses into individual records containing:

* respondent identifier
* awareness category
* awareness value
* associated reporting dimensions

This produces a much narrower analytical table where awareness becomes a row attribute rather than another column.

The resulting structure allows Excel Pivot Tables to perform straightforward **Distinct Count of Subject Numbers** grouped by awareness category, significantly reducing pivot complexity while improving refresh performance.

This transformation was introduced specifically to optimise downstream reporting rather than alter the underlying survey data.

---

# Data Loading

After transformation, each module appends its processed dataset directly into MySQL.

The loading process includes:

* dataframe validation
* insertion of the reporting period
* table-specific loading
* append-based incremental updates

Typical loading operation:

```python
merged_df.to_sql(
    con=my_conn,
    name='brand_awareness',
    if_exists='append',
    index=False
)
```

Appending data rather than replacing tables preserves historical tracking while allowing new survey responses to be incorporated continuously.

---

# Configuration

The project uses a JSON configuration file to separate sensitive credentials from application logic.

Configuration includes:

* API username
* API password
* Survey ID
* Database server
* Database username
* Database password
* Database name
* Database port

This approach keeps deployment flexible across different environments while avoiding hard-coded credentials within the application.

---

# Error Handling

The pipeline includes lightweight validation to improve execution reliability.

Examples include:

* empty respondent lists
* missing survey responses
* invalid date selections
* transformation failures
* database loading exceptions

Where no interviews exist for a selected day, the process reports the condition and proceeds without terminating the entire execution.

---

# Execution Workflow

```
Authenticate
      │
      ▼
Load Configuration
      │
      ▼
Retrieve Respondent IDs
      │
      ▼
Download Individual Survey
      │
      ▼
Transform JSON Responses
      │
      ▼
Create DataFrame
      │
      ▼
Insert Reporting Period
      │
      ▼
Append to MySQL
```

---

# Project Structure

```
Nutrifoods Brand Health Tracking
│
├── main_argparse.py
├── functions2.py
├── brand_aware_expansion.py
├── credentials_2.json
│
├── Survey Transformations
│   ├── Recruitment Profile
│   ├── Social Profile
│   ├── Brand Awareness
│   ├── Brand Impression
│   ├── Media Habits
│   └── Brand Preference
│
└── MySQL Output Tables
```

---

# Key Features

* Automated STG API integration
* Modular survey processing
* Configurable date-range extraction
* Independent transformation workflows
* Incremental MySQL loading
* Reporting-period tagging
* Reporting-optimised Brand Awareness Expansion
* Excel Pivot Table–friendly data structures
* Separation of configuration from application logic

---

# Future Improvements

Potential enhancements include:

* configurable logging framework
* retry mechanisms for transient API failures
* parallel download processing where API limits permit
* automated duplicate detection prior to database insertion
* execution summaries with processing statistics
* configuration-driven survey module registration for easier extensibility

---

# Outcome

The Nutrifoods Brand Health Tracking project transformed a manual survey extraction process into a repeatable ETL workflow capable of producing clean, structured datasets directly from the STG platform.

Its modular architecture enables each survey section to be refreshed independently, while the introduction of the **Brand Awareness Expansion** transformation demonstrates a practical optimisation for analytical reporting. By reshaping wide awareness datasets into a format better suited to pivot-based aggregation, the project significantly simplified respondent counting and improved reporting efficiency without altering the integrity of the underlying survey data.
