# Alcohol Retail Product Tracking ETL Pipeline

## Project Overview

This project automates the extraction, transformation and consolidation of alcohol retail survey data collected through the STG mobile data collection platform. The solution was developed to transform product-level field observations into a unified analytical dataset suitable for downstream reporting and market analysis.

Unlike conventional survey downloads where each respondent generates a single record, this study collected detailed information for multiple alcoholic beverage products within the same interview. Each product contained its own set of repeated survey questions, resulting in multiple product-specific datasets that required independent processing before being combined into a single reporting structure.

The project eliminates manual data preparation by automatically downloading survey responses, transforming product observations into standardized tables, and consolidating them into an analysis-ready database.

---

## Business Problem

Retail audits frequently capture information for numerous products during a single store visit. Each beverage product is associated with its own repeated survey block containing information such as:

* Product identification
* Brand
* Package size
* Availability
* Pricing
* Promotional activity
* Product-specific observations

While the STG platform stores these responses correctly, the exported data naturally reflects the survey structure rather than an analyst-friendly format.

This created several challenges:

* Product observations were distributed across multiple repeated survey sections.
* Similar information existed across numerous product blocks.
* Individual product datasets needed to be standardised before consolidation.
* Analysts required a single product-level table rather than numerous fragmented exports.

Without automation, preparing these datasets required extensive manual manipulation before analysis could begin.

---

## Solution

A modular ETL pipeline was developed to automate the complete processing workflow.

The pipeline:

1. Authenticates with the STG API.
2. Downloads survey responses for each product-specific questionnaire.
3. Extracts repeated survey sections independently.
4. Applies product-specific transformation logic.
5. Standardises variable names and data structures across products.
6. Merges all processed products into a unified analytical dataset.
7. Loads the final tables into MySQL for reporting.

By treating each product section independently before consolidation, the solution maintains data integrity while producing a clean product-level dataset suitable for business analysis.

---

## Workflow

```
STG Survey Platform
        │
        ▼
Download Product Responses
        │
        ▼
Product-Specific Transformations
        │
        ▼
Standardise Field Structures
        │
        ▼
Combine All Product Records
        │
        ▼
Quality Validation
        │
        ▼
MySQL Analytical Tables
```

---

## Key Features

### Product-Level Data Extraction

Each beverage product was processed independently, allowing repeated survey sections to be extracted without introducing ambiguity between products.

### Modular Transformation Pipeline

Transformation logic was separated into reusable routines, making it easier to maintain processing rules as new products or survey revisions were introduced.

### Schema Standardisation

Although products originated from separate survey blocks, the pipeline converted them into a consistent structure, enabling straightforward aggregation and comparison across the complete product portfolio.

### Automated Dataset Consolidation

After transformation, all product datasets were merged into a single analytical table, removing the need for manual copy-and-paste operations traditionally required during reporting cycles.

### Database Integration

Processed datasets were written directly into MySQL, providing analysts with a structured and query-ready repository for downstream reporting and dashboard development.

---

## Technical Highlights

* Python ETL automation
* REST API integration
* Survey data extraction
* Product-level transformation pipelines
* Repeated survey block handling
* Data standardisation
* Automated dataset consolidation
* Pandas data processing
* MySQL integration
* Error handling and validation
* Modular ETL architecture

---

## Challenges Addressed

One of the primary challenges involved the repeated nature of the survey instrument. Rather than producing a single flat export, product observations were embedded within multiple product-specific sections that shared similar question structures.

To address this, the processing pipeline isolated each product block, transformed it independently, and then consolidated all outputs into a unified schema. This approach significantly simplified maintenance, reduced transformation complexity, and ensured that new product sections could be incorporated with minimal changes to the overall workflow.

---

## Outcome

The completed solution replaced a labour-intensive manual preparation process with a fully automated ETL workflow capable of generating consistent, product-level analytical datasets directly from field survey responses.

The resulting database provides analysts with a clean and standardised view of alcohol retail observations, enabling faster reporting, easier product comparisons, and more reliable market analysis while substantially reducing the time required to prepare survey data for business use.

---
