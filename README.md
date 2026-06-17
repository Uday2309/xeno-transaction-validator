# 🚀 Xeno Transaction Data Validation Platform

A web-based transaction validation and processing platform built using **Python, Streamlit, and Pandas**.

This application validates transaction datasets, identifies data quality issues, generates cleaned outputs, and automatically splits large files into manageable chunks for efficient processing.

---

## 📌 Project Overview

Organizations often receive transaction data from multiple sources and countries. Before such data can be used for analytics, reporting, or operational workflows, it must be validated and standardized.

This platform helps ensure data quality by:

* Validating phone numbers using country-specific rules
* Validating date and time formats
* Detecting invalid payment modes
* Identifying duplicate transactions
* Checking numeric fields such as amount and quantity
* Generating downloadable cleaned datasets
* Splitting large files into smaller chunks

---

## ✨ Features

### Data Upload

* Upload transaction datasets in CSV format
* Preview uploaded data before processing

### Country-Specific Phone Validation

Supported examples:

| Country        | Rule      |
| -------------- | --------- |
| India (IN)     | 10 digits |
| Singapore (SG) | 8 digits  |

Validation rules are configurable through:

```json
validation_rules.json
```

### Date & Time Validation

Supported formats:

Dates:

* DD-MM-YYYY
* YYYY-MM-DD
* DD/MM/YYYY

Times:

* HH:MM
* HH:MM:SS

### Data Integrity Checks

The platform validates:

* Missing Order IDs
* Missing Product IDs
* Invalid Phone Numbers
* Invalid Dates
* Invalid Times
* Invalid Payment Modes
* Negative Amounts
* Invalid Quantities
* Duplicate Transactions

### Output Generation

After validation:

✅ Cleaned CSV generated

✅ Rejected rows report generated

✅ Validation summary displayed

✅ Chunked CSV files generated

---

## 🛠 Tech Stack

### Frontend

* Streamlit

### Backend

* Python

### Data Processing

* Pandas

### Validation Engine

* Custom Rule-Based Validation

---

## 📂 Project Structure

```text
Xeno_Part4/
│
├── app.py
├── validation_rules.json
├── requirements.txt
├── transactions.csv
├── README.md
│
├── uploads/
└── outputs/
```

---

## ⚙️ Installation

Clone the repository:

```bash
git clone <repository-url>
```

Navigate to the project:

```bash
cd xeno-transaction-validator
```

Create virtual environment:

```bash
python -m venv venv
```

Activate virtual environment:

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

Start Streamlit:

```bash
streamlit run app.py
```

Application will be available at:

```text
http://localhost:8501
https://xeno-transaction-validator-gepk7maga9wmk53jc5bq3m.streamlit.app

```

---

## 📊 Sample Workflow

1. Upload transaction CSV
2. Map dataset columns
3. Configure country validation rules
4. Run validation
5. Review validation summary
6. Download cleaned output
7. Download rejected records
8. Download chunked files

---

## 📈 Validation Outputs

The application provides:

* Total Rows Processed
* Valid Rows
* Rejected Rows
* Duplicate Transactions
* Validation Error Summary
* Downloadable Reports

---

## 🔮 Future Enhancements

Potential improvements include:

* Database integration (MySQL/PostgreSQL)
* User authentication
* API-based validation services
* Cloud storage integration
* Advanced analytics dashboard
* Multi-file batch processing

---

## 👨‍💻 Author

**Uday Kumar Dubey**

B.E. Computer Science & Business Systems
Chandigarh University

---

## 📄 Assignment Context

Developed as part of the **Xeno Implementation Internship Assignment**.

The project demonstrates practical skills in:

* Data Validation
* Data Cleaning
* Data Transformation
* Data Quality Assurance
* CSV Processing
* Web-Based Workflow Design
