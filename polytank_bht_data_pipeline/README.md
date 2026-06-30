# Polytank Brand Health Tracking

## Overview

The **Polytank Brand Health Tracking** project is an automated data ingestion and transformation pipeline developed to retrieve consumer brand health survey data from the STG Survey Platform, transform the raw API responses into structured analytical datasets, and load the processed data into a MySQL database.

The project supports continuous monitoring of key brand health indicators by collecting multiple survey modules relating to brand awareness, perception, media consumption, consumer profiles, and product preference. The resulting datasets form the foundation for downstream reporting, dashboard development, and marketing analytics.

Unlike one-off survey exports, this pipeline was designed to support repeatable data collection with configurable date ranges and modular execution.

---

# Business Objective

The primary objective of this project is to automate the extraction of Polytank's consumer research data while maintaining a standardized database structure for reporting and analysis.

The pipeline eliminates the need for manual data exports by:

* Downloading completed survey responses directly from the STG API
* Transforming nested survey responses into relational datasets
* Standardizing variable naming and formatting
* Loading cleaned datasets directly into MySQL
* Supporting incremental daily or historical data downloads

The project enables marketing and research teams to focus on analysis rather than data preparation.

---

# Project Structure

```
Polytank_Brand_Health/
│
├── scheduler.py
├── main_argparse.py
├── functions2.py
├── credentials_2.json
│
├── logs/
│
└── MySQL Database
      ├── recruit_profile
      ├── owner_overview
      ├── brand_awareness
      ├── owner_impression
      ├── media
      └── tank_preferences
```

---

# System Architecture

```
                 Windows Terminal
                        │
                        ▼
                scheduler.py (Optional)
                        │
        Sequential execution of survey modules
                        │
                        ▼
                 main_argparse.py
                        │
                Argument Validation
                        │
                        ▼
          DownloadDetails & RecruitmentDownload
                        │
              STG Survey Platform API
                        │
              Retrieve Respondent IDs
                        │
                        ▼
          Survey-specific Transformation
                        │
                Pandas DataFrame
                        │
                        ▼
                 SQLAlchemy Engine
                        │
                        ▼
                  MySQL Database
```

---

# Core Components

## 1. scheduler.py

Acts as an orchestration layer responsible for sequentially executing multiple survey extraction jobs.

Responsibilities include:

* Running each survey module independently
* Passing date arguments to the extraction script
* Applying configurable delays between API calls
* Logging execution status
* Monitoring execution time
* Preventing long-running tasks using configurable timeouts

The scheduler itself performs no data transformation; it simply coordinates executions of `main_argparse.py`.

---

## 2. main_argparse.py

This serves as the primary entry point of the application.

Its responsibilities include:

* Parsing command-line arguments
* Establishing database connectivity
* Authenticating against the STG API
* Downloading respondent IDs
* Calling the appropriate transformation routine
* Loading processed data into MySQL

Supported command-line syntax:

```bash
python main_argparse.py -f recruit_profile -s 2026-01-23 -e 2026-01-23
```

---

## 3. functions2.py

Contains the business logic responsible for interacting with the STG API and transforming raw survey responses into structured Pandas DataFrames.

Major responsibilities include:

* API communication
* XML/JSON response parsing
* Data extraction
* Variable standardization
* Cleaning missing values
* Building relational datasets

This module contains the majority of the project's domain-specific transformation logic.

---

# Supported Survey Modules

The pipeline currently supports six independent survey datasets.

| Module          | Purpose                                           | Database Table   |
| --------------- | ------------------------------------------------- | ---------------- |
| recruit_profile | Respondent demographic profile                    | recruit_profile  |
| tank_social     | Respondent overview and ownership characteristics | owner_overview   |
| brand_aware     | Brand awareness and recall                        | brand_awareness  |
| brand_impress   | Brand perception and impressions                  | owner_impression |
| media           | Media consumption habits                          | media            |
| tank_preference | Preferred tank brand and reasons                  | tank_preferences |

Each module can be executed independently using the `-f` command-line argument.

---

# Processing Workflow

For each selected survey module, the pipeline performs the following steps:

### Step 1

Authenticate with the STG Survey Platform using stored credentials.

↓

### Step 2

Retrieve respondent/store IDs for the selected date.

↓

### Step 3

Download individual survey responses.

↓

### Step 4

Transform raw survey responses into structured DataFrames.

↓

### Step 5

Merge all processed respondents into a consolidated dataset.

↓

### Step 6

Insert a reporting Period column.

↓

### Step 7

Append records into the corresponding MySQL table.

---

# Database Outputs

Each survey module loads into a dedicated relational table.

| Table            | Description                           |
| ---------------- | ------------------------------------- |
| recruit_profile  | Respondent demographics               |
| owner_overview   | Household and tank ownership overview |
| brand_awareness  | Brand awareness metrics               |
| owner_impression | Brand perception metrics              |
| media            | Media usage behaviour                 |
| tank_preferences | Brand preference analysis             |

Using separate tables simplifies downstream SQL analysis and dashboard development.

---

# Configuration

The pipeline requires a configuration file (`credentials_2.json`) containing:

* STG API username
* STG API password
* Survey ID
* API key
* MySQL server
* Database name
* Username
* Password
* Port

Keeping credentials external to the source code improves maintainability and simplifies deployment across environments.

---

# Execution Modes

## Production Workflow (Recommended)

The recommended production workflow is to execute individual survey modules manually using `main_argparse.py`.

This approach has consistently proven to be the most reliable for operational data collection, particularly when processing historical or multi-day datasets. Executing one survey module at a time allows operators to monitor API responses, identify failures early, and rerun only the affected extraction if necessary.

Example:

```bash
python main_argparse.py -f media -s 2026-01-23 -e 2026-01-23
```

---

## Automated Scheduler (Prototype)

To reduce repetitive manual execution, an orchestration layer (`scheduler.py`) was developed.

The scheduler sequentially invokes `main_argparse.py` for each configured survey module while introducing configurable delays and task timeouts to reduce API pressure.

Implemented features include:

* Sequential task execution
* Configurable execution timeout
* Delay between API requests
* Execution logging
* Command-line date overrides
* Independent task execution

Although the scheduler successfully coordinated multiple survey downloads, operational testing identified inconsistent behaviour during larger batched date extractions. These inconsistencies were likely influenced by a combination of network reliability, API responsiveness, and Windows Task Scheduler execution characteristics.

For this reason, the scheduler remains part of the project as an automation prototype and engineering utility, while manual execution continues to be the preferred production workflow.

---

# Error Handling

The pipeline incorporates several mechanisms to improve operational robustness:

* Command-line argument validation
* Exception handling for missing survey responses
* Timeout protection for long-running tasks
* Execution logging
* Graceful handling of empty downloads
* Independent execution of survey modules to minimise cascading failures

---

# Technologies Used

| Component              | Technology            |
| ---------------------- | --------------------- |
| Programming Language   | Python                |
| API Communication      | HTTP Requests         |
| Data Processing        | Pandas                |
| Database Connectivity  | SQLAlchemy            |
| Database               | MySQL                 |
| Scheduling Prototype   | Python Scheduler      |
| Configuration          | JSON                  |
| Logging                | Python Logging Module |
| Command Line Interface | argparse              |

---

# Engineering Notes

This project evolved through several iterations aimed at improving automation and operational reliability.

The initial implementation relied entirely on manual execution of extraction scripts. This was later enhanced with a parameterized command-line interface (`main_argparse.py`), enabling flexible execution across different survey modules and date ranges.

To further reduce manual effort, a scheduler (`scheduler.py`) was introduced as an orchestration layer capable of executing all survey modules sequentially with configurable delays and execution timeouts. The scheduler also served as the intended entry point for integration with Windows Task Scheduler for unattended execution.

While the scheduler functioned as designed, extended testing with larger batched date ranges revealed intermittent reliability issues that were difficult to attribute to a single cause. Potential contributing factors included network stability, API responsiveness, long-running extraction sessions, and Windows Task Scheduler behaviour.

Based on these operational observations, the project retained the scheduler as a prototype automation component while adopting manual execution through `main_argparse.py` as the production-standard workflow. This decision prioritizes reliability, simplifies troubleshooting, and provides greater operational control during data collection.

The modular architecture nevertheless leaves the project well-positioned for future enhancements, such as retry mechanisms, checkpointing, incremental processing, or migration to a more robust enterprise scheduling platform.

---

# Future Improvements

Potential enhancements include:

* Automatic retry logic for failed downloads
* Checkpointing to resume interrupted executions
* Incremental data synchronization
* Enhanced API rate-limit management
* Parallel processing where API constraints permit
* Configuration via environment variables
* Containerized deployment using Docker
* Enterprise scheduling through Windows Services, Cron, or cloud orchestration platforms

---

# Maintenance Notes

* Validate API credentials periodically.
* Monitor schema changes in the STG survey instrument.
* Review transformation logic whenever questionnaires are updated.
* Periodically archive execution logs.
* Validate database constraints before loading historical data.
* Retain the scheduler as an automation foundation for future improvements while continuing to use manual execution for production workloads.
