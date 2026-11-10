---
policy_code: "POL-LWP-04"
title: "Unpaid Leave & Loss of Pay (LOP) Policy"
leave_type: "unpaid"
annual_allowance: 0
max_consecutive_days: 30
notice_period_days: 3
is_paid: false
deduction_rate: "prorated_daily"
requires_manager_approval: true
tags: ["unpaid", "lop", "loss-of-pay", "salary-deduction"]
last_updated: "2026-11-06"
---

# Unpaid Leave & Loss of Pay (LOP) Policy

## 1. Application Conditions
- Unpaid leave applies when an employee exhausts their accrued paid balance or requests voluntary leave without pay.
- Prior approval from HR and the reporting manager is mandatory.

## 2. Deterministic Payroll Deduction Formula
- In accordance with Section 4.2 of the WorkforceAI Deterministic Payroll Engine:
  - Daily Proration Rate = `Monthly Basic Salary / Total Working Days in Month`
  - Unpaid Leave Deduction = `Daily Proration Rate * Approved Unpaid Days`
- Statutory contributions (TDS/Tax and PF) are recalculated on the adjusted gross earnings.
