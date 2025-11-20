# TrustChain Fairness Algorithms - Application Guide

## Overview

The fairness algorithms we built can be applied to **any high-stakes decision** where bias could harm people. Here are real-world applications:

---

## 🏢 Corporate Applications

### 1. Promotions & Performance Reviews
**Problem:** Managers unconsciously favor certain demographics for promotions.

**Fairness Tests:**
```python
# Demographic Parity: Are promotion rates equal across groups?
analyzer = DemographicParityAnalyzer(max_disparity=0.15)
promotion_decisions = {
    "male": ["promoted", "promoted", "not_promoted", ...],
    "female": ["not_promoted", "not_promoted", "promoted", ...],
}
result = analyzer.analyze(promotion_decisions)
# Alerts if women promoted 15% less than men
```

**Counterfactual Test:**
```python
# Does promotion decision change if we change gender/race?
tester = CounterfactualFairnessTester()
result = await tester.test_decision(
    decision_func=evaluate_for_promotion,
    input_data={"performance_score": 4.5, "years_experience": 5, "gender": "female"},
    protected_attrs=["gender", "race", "age"]
)
# Flags if changing gender changes promotion decision
```

**Individual Fairness:**
```python
# Do employees with similar performance get similar outcomes?
tester = IndividualFairnessTester()
cases = [
    ({"performance": 4.5, "experience": 5}, "promoted"),
    ({"performance": 4.6, "experience": 5}, "not_promoted"),  # Very similar!
]
result = tester.test_fairness(cases)
# Detects inconsistent promotion decisions
```

---

### 2. Hiring & Recruitment
**Problem:** AI resume screening tools discriminate against certain names, schools, or backgrounds.

**Application:**
```python
# Test if hiring rates differ by university prestige
decisions_by_school = {
    "ivy_league": ["hired"] * 15 + ["rejected"] * 5,      # 75%
    "state_university": ["hired"] * 8 + ["rejected"] * 12  # 40%
}
result = analyzer.analyze(decisions_by_school)
# Alerts to 35% disparity - potential prestige bias
```

**Real Impact:** Prevents discrimination based on:
- Name (ethnic/racial bias)
- University (socioeconomic bias)
- Employment gaps (pregnancy/disability bias)
- Age (ageism in tech)

---

### 3. Salary & Compensation
**Problem:** Pay gaps persist across gender and race.

**Application:**
```python
# Individual fairness for salary decisions
cases = [
    ({"role": "engineer", "experience": 5, "performance": 4.5, "gender": "male"}, 120000),
    ({"role": "engineer", "experience": 5, "performance": 4.5, "gender": "female"}, 95000),
]
result = tester.test_fairness(cases, weights={"gender": 0.0})  # Gender shouldn't matter
# Detects $25k gender pay gap for identical qualifications
```

---

## 💼 Business & Finance

### 4. Business Loan Approvals
**Problem:** Small businesses owned by minorities get denied more often.

**Application:**
```python
decisions_by_owner = {
    "white_male": ["approved"] * 16 + ["denied"] * 4,     # 80%
    "black_female": ["approved"] * 9 + ["denied"] * 11    # 45%
}
result = analyzer.analyze(decisions_by_owner)
# Flags 35% disparity in loan approval rates
```

---

### 5. Venture Capital Funding
**Problem:** Female founders receive <3% of VC funding.

**Application:**
```python
# Test if funding decisions change based on founder demographics
tester = CounterfactualFairnessTester()
result = await tester.test_decision(
    decision_func=evaluate_startup_pitch,
    input_data={
        "revenue": 500000,
        "growth_rate": 0.3,
        "team_size": 10,
        "founder_gender": "female"
    },
    protected_attrs=["founder_gender", "founder_race"]
)
# Detects if identical pitch gets rejected when founder is female
```

---

### 6. Insurance Pricing
**Problem:** Zip code-based pricing discriminates against minorities.

**Application:**
```python
# Demographic parity for insurance rates
decisions_by_neighborhood = {
    "predominantly_white": [800, 850, 820, ...],  # Avg $823
    "predominantly_black": [1200, 1250, 1180, ...]  # Avg $1210
}
# Detects 47% price disparity for similar risk profiles
```

---

## 🏛️ Government & Public Services

### 7. College Admissions
**Problem:** Legacy admissions favor wealthy white students.

**Application:**
```python
# Test if admission decision changes based on legacy status
decisions_by_legacy = {
    "legacy_student": ["admitted"] * 18 + ["rejected"] * 2,  # 90%
    "non_legacy": ["admitted"] * 10 + ["rejected"] * 10      # 50%
}
result = analyzer.analyze(decisions_by_legacy)
# Flags 40% advantage for legacy students
```

---

### 8. Criminal Justice & Sentencing
**Problem:** Racial disparities in sentencing for same crimes.

**Application:**
```python
# Individual fairness for sentencing
cases = [
    ({"crime": "theft", "prior_record": 0, "race": "white"}, "probation"),
    ({"crime": "theft", "prior_record": 0, "race": "black"}, "6_months_jail"),
]
result = tester.test_fairness(cases)
# Detects racial disparity in sentencing for identical cases
```

---

### 9. Parole & Bail Decisions
**Problem:** COMPAS algorithm discriminates against Black defendants.

**Application:**
```python
# Counterfactual fairness for bail
result = await tester.test_decision(
    decision_func=calculate_flight_risk,
    input_data={"charges": "theft", "ties_to_community": "high", "race": "black"},
    protected_attrs=["race"]
)
# Ensures race doesn't affect bail amount
```

---

## 🏥 Healthcare

### 10. Medical Treatment Allocation
**Problem:** Kidney transplant waitlists favor certain demographics.

**Application:**
```python
# Demographic parity for organ allocation
decisions_by_race = {
    "white": ["received_organ"] * 14 + ["waitlist"] * 6,  # 70%
    "black": ["received_organ"] * 8 + ["waitlist"] * 12   # 40%
}
result = analyzer.analyze(decisions_by_race)
# Flags 30% disparity in organ allocation
```

---

### 11. Clinical Trial Selection
**Problem:** Trials underrepresent minorities and women.

**Application:**
```python
# Ensure diverse trial enrollment
decisions_by_gender = {
    "male": ["enrolled"] * 16 + ["excluded"] * 4,    # 80%
    "female": ["enrolled"] * 12 + ["excluded"] * 8   # 60%
}
result = analyzer.analyze(decisions_by_gender)
# Alerts to gender imbalance in trial enrollment
```

---

## 🏠 Housing & Real Estate

### 12. Rental Applications
**Problem:** Landlords discriminate based on names, source of income.

**Application:**
```python
# Test if approval changes based on applicant name
tester = CounterfactualFairnessTester()
result = await tester.test_decision(
    decision_func=evaluate_rental_application,
    input_data={
        "income": 60000,
        "credit_score": 720,
        "name": "Jamal Washington"  # Stereotypically Black name
    },
    protected_attrs=["name"]  # Proxy for race
)
# Detects if "John Smith" gets approved but "Jamal Washington" denied
```

---

### 13. Mortgage Approvals
**Problem:** Redlining still exists through algorithmic bias.

**Application:**
```python
decisions_by_neighborhood = {
    "white_neighborhood": ["approved"] * 17 + ["denied"] * 3,  # 85%
    "minority_neighborhood": ["approved"] * 11 + ["denied"] * 9  # 55%
}
result = analyzer.analyze(decisions_by_neighborhood)
# Flags 30% disparity - potential redlining
```

---

## 🎓 Education

### 14. Scholarship Awards
**Problem:** Merit scholarships favor students from wealthy schools.

**Application:**
```python
# Individual fairness for scholarship decisions
cases = [
    ({"gpa": 3.8, "sat": 1400, "school_type": "private"}, "awarded"),
    ({"gpa": 3.8, "sat": 1400, "school_type": "public"}, "denied"),
]
result = tester.test_fairness(cases)
# Detects bias against public school students
```

---

### 15. Teacher Performance Evaluations
**Problem:** Teachers in low-income schools rated lower.

**Application:**
```python
decisions_by_school_income = {
    "high_income_school": [4.5, 4.7, 4.6, ...],  # Avg 4.6
    "low_income_school": [3.2, 3.5, 3.4, ...]    # Avg 3.4
}
# Detects if evaluation system penalizes teachers in challenging schools
```

---

## 🚔 Law Enforcement

### 16. Predictive Policing
**Problem:** Algorithms over-police minority neighborhoods.

**Application:**
```python
# Demographic parity for police deployment
decisions_by_neighborhood = {
    "white_neighborhood": ["high_patrol"] * 3 + ["low_patrol"] * 17,  # 15%
    "black_neighborhood": ["high_patrol"] * 14 + ["low_patrol"] * 6   # 70%
}
result = analyzer.analyze(decisions_by_neighborhood)
# Flags 55% disparity in policing intensity
```

---

## 🌐 Technology & Social Media

### 17. Content Moderation
**Problem:** Posts from minorities flagged more often.

**Application:**
```python
decisions_by_user_demographics = {
    "majority_users": ["flagged"] * 5 + ["not_flagged"] * 95,    # 5%
    "minority_users": ["flagged"] * 20 + ["not_flagged"] * 80    # 20%
}
result = analyzer.analyze(decisions_by_user_demographics)
# Detects 15% disparity in content flagging
```

---

### 18. Ad Targeting & Job Postings
**Problem:** Facebook showed housing/job ads only to certain races.

**Application:**
```python
# Ensure job ads shown equally across demographics
ad_delivery = {
    "male_users": ["shown"] * 18 + ["not_shown"] * 2,    # 90%
    "female_users": ["shown"] * 10 + ["not_shown"] * 10  # 50%
}
result = analyzer.analyze(ad_delivery)
# Flags gender bias in ad delivery algorithm
```

---

## 📊 Implementation Template

For any new use case, follow this pattern:

```python
from services.fairness_testing import (
    CounterfactualFairnessTester,
    DemographicParityAnalyzer,
    IndividualFairnessTester
)

# 1. Define your decision function
async def make_decision(input_data):
    # Your AI/algorithm decision logic
    return decision

# 2. Test Counterfactual Fairness
cf_tester = CounterfactualFairnessTester()
cf_result = await cf_tester.test_decision(
    decision_func=make_decision,
    input_data=base_case,
    protected_attrs=["race", "gender", "age", ...]
)

# 3. Test Demographic Parity
dp_analyzer = DemographicParityAnalyzer(max_disparity=0.15)
dp_result = dp_analyzer.analyze(decisions_by_group)

# 4. Test Individual Fairness
if_tester = IndividualFairnessTester(similarity_threshold=0.9)
if_result = if_tester.test_fairness(cases_with_decisions)

# 5. Take action on results
if not cf_result.passed:
    alert_compliance_team(cf_result)
    require_human_review()

if not dp_result.passed:
    investigate_systemic_bias(dp_result)
    
if not if_result.passed:
    audit_decision_consistency(if_result)
```

---

## 🎯 Key Principles

**When to Apply:**
- ✅ Decision affects people's lives (jobs, loans, housing, etc.)
- ✅ Protected attributes could influence decision
- ✅ Historical bias exists in this domain
- ✅ Automated/AI system making decisions

**What to Test:**
1. **Counterfactual:** Does decision change if we flip protected attributes?
2. **Demographic Parity:** Are approval rates similar across groups?
3. **Individual Fairness:** Do similar people get similar outcomes?

**Thresholds to Use:**
- **Low-stakes:** 20-25% disparity acceptable
- **Medium-stakes:** 15% disparity threshold
- **High-stakes:** 10% disparity threshold
- **Critical (life-altering):** 5% disparity threshold

---

## 🚀 Next Steps

1. **Identify your use case** from the list above
2. **Collect historical decisions** by demographic groups
3. **Run fairness tests** using the template
4. **Set up monitoring** to track metrics over time
5. **Implement alerts** when thresholds exceeded
6. **Require human review** for flagged cases

---

## 📚 Additional Resources

- **Legal Compliance:** EEOC guidelines, Fair Housing Act, ECOA
- **Technical Standards:** IEEE P7003, NIST AI Risk Management
- **Research:** Fairness definitions (Dwork et al., Hardt et al.)

---

**TrustChain fairness algorithms are ready to prevent discrimination in any high-stakes AI decision system.** 🛡️
