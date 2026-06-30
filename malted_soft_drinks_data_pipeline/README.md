# Beverage Retail Execution Tracking Pipeline

## Overview

This project is an automated ETL pipeline developed to process retail execution survey data collected through the STG Mobile platform for a beverage manufacturer.

The survey captures outlet-level execution metrics across a predefined portfolio of beverage products, including product availability, retail pricing, stock status, outlet branding, refrigeration assets, and respondent profile information.

Rather than exporting raw XML files for manual processing, this solution automatically retrieves completed interviews through the STG API, transforms the XML responses into structured analytical datasets, and loads the results into MySQL for downstream reporting.

The project was designed around modular extraction routines so that each business dataset can be refreshed independently without affecting the remaining tables.

---

## Business Objectives

The pipeline supports several operational monitoring activities:

- Measure retail availability of key beverage SKUs
- Monitor retail selling prices across outlets
- Identify out-of-stock products
- Track branded outlet visibility
- Monitor refrigerator deployment
- Capture outlet profiling information
- Produce analysis-ready datasets for commercial reporting

---

## Project Architecture

```
STG Mobile Survey
        │
        ▼
Retrieve Subject IDs
        │
        ▼
Download XML Interviews
        │
        ▼
XML Parsing Engine
        │
        ▼
Transformation Modules
        │
        ├── Recruitment Profile
        ├── Outlet Description
        ├── Product Availability
        ├── Product Pricing
        └── Product Stock Status
        │
        ▼
Normalized DataFrames
        │
        ▼
MySQL Database
```

---

## Features

### Recruitment Profile

Extracts outlet-level metadata including:

- Enumerator
- Region
- Outlet name
- Outlet code
- Visit dates
- GPS coordinates
- Survey duration
- Upload timestamps

GPS coordinates are parsed into separate latitude, longitude, altitude, bearing and speed fields for easier geographic analysis.

---

### Outlet Description

Captures merchandising information including:

- Branded outlet status
- Brand ownership
- Visibility materials
- Refrigerator deployment
- Branded assets
- Asset counts

Repeated branding observations are transformed into structured rows, while multiselect brand responses are automatically exploded into individual records for easier reporting.

---

### Product Availability

Determines whether each monitored beverage SKU was available during the outlet visit.

The transformation converts repeated XML product responses into a single structured dataset where every monitored SKU occupies its own analytical field.

---

### Product Pricing

Extracts the selling price recorded for each monitored beverage SKU.

The resulting dataset allows pricing comparisons across:

- Regions
- Outlet types
- Individual products
- Survey periods

---

### Product Stock Status

Captures whether products were currently in stock during the visit.

This dataset supports out-of-stock analysis and retail execution monitoring across the product portfolio.

---

## Technical Workflow

For each survey day the pipeline performs the following steps:

1. Retrieve completed interview IDs from STG.
2. Download XML responses for each interview.
3. Parse XML into a structured list.
4. Extract only the required variables.
5. Transform repeated survey sections into structured DataFrames.
6. Merge interview metadata with business variables.
7. Standardize timestamps and GPS information.
8. Load transformed datasets into MySQL.

---

## Reusable ETL Framework

The solution was designed around reusable helper functions that standardize data extraction across every survey module.

Core helper methods include:

- Retrieval of survey interview IDs
- XML interview downloads
- XML parsing
- Data formatting utilities
- Multi-select response expansion

This modular approach minimizes duplicated code and simplifies maintenance when survey questionnaires change.

---

## Data Processing Techniques

The pipeline incorporates several transformation techniques, including:

- XML parsing into structured tables
- Dynamic variable extraction
- Sequential XML node matching
- Dictionary-based record construction
- Multi-response expansion
- GPS parsing using regular expressions
- Timestamp normalization
- DataFrame merging
- Automated SQL loading

---

## Output Tables

The pipeline produces independent analytical tables including:

- recruit_profile
- outlet_describe
- product_availability
- product_price
- product_status

Each table is optimized for downstream querying and reporting.

---

## Technologies Used

- Python
- Pandas
- Requests
- XML ElementTree
- NumPy
- SQLAlchemy
- MySQL
- Regular Expressions (Regex)
- STG Survey API

---

## Key Achievements

- Automated retrieval of retail execution survey data from STG.
- Eliminated manual XML processing.
- Built reusable ETL utilities shared across multiple transformations.
- Standardized XML parsing into structured relational datasets.
- Automated extraction of merchandising, pricing, availability and stock information.
- Normalized repeated survey responses into reporting-ready tables.
- Improved maintainability through modular transformation functions.
- Delivered analysis-ready datasets suitable for commercial reporting and retail performance monitoring.
