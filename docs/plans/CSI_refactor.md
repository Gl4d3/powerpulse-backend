# PowerPulse Analytics: CSI Calculation Strategy

**Objective:** This document outlines the strategic evolution of the PowerPulse analytics engine from its current state, which focuses on transactional metrics like CSAT and FCR, to a more sophisticated, holistic **Customer Satisfaction Index (CSI)** model.

---

### **1. The Old Approach (Current System)**

The current PowerPulse backend provides a strong foundation for customer service analytics. It calculates satisfaction based on a few key, direct metrics derived from AI analysis.

#### **Core Metrics:**

*   **Satisfaction Score (`satisfaction_score`):** A single score (1-5) returned by the AI, representing the overall satisfaction of a conversation. This functions as a traditional **CSAT (Customer Satisfaction Score)**.
*   **Is Satisfied (`is_satisfied`):** A boolean flag, typically true if the `satisfaction_score` is 4 or 5. This is used to calculate the overall CSAT percentage for the dashboard.
*   **First Contact Resolution (`first_contact_resolution`):** A boolean flag indicating if the AI determined the issue was resolved in the first interaction.

#### **Calculation Flow:**

1.  An AI service (Gemini/GPT) analyzes a conversation.
2.  It returns a single satisfaction score and a boolean FCR flag.
3.  These values are stored directly in the `Conversation` database table.
4.  The analytics service aggregates these values (e.g., calculates the percentage of `is_satisfied=true`) for the dashboard.

#### **Limitations of the Old Approach:**

*   **One-Dimensional:** A single satisfaction score doesn't explain *why* a customer was satisfied or dissatisfied. Was the agent fast but unhelpful? Empathetic but slow? The score alone doesn't tell us.
*   **Lacks Diagnostic Power:** When the overall CSAT score drops, it's difficult to pinpoint the root cause. Is it an issue with resolution quality, agent tone, or service speed?
*   **Subjective to AI Model:** The entire outcome rests on a single, broad judgment from the AI, which can be less reliable than scoring multiple, specific attributes.

---

### **2. The New Approach (Proposed CSI Model)**

The new approach implements a **Customer Satisfaction Index (CSI)**, a composite, weighted score derived from four distinct pillars of service quality. This provides a multi-dimensional and far more actionable view of performance.

#### **The Four Pillars of Service Quality:**

The CSI is built by measuring and weighting these four categories:

| Pillar | What It Measures | Constituent Micro-Metrics |
| :--- | :--- | :--- |
| **1. EFFECTIVENESS / Resolution Quality** | Was the customer's issue successfully resolved? | • `resolution_achieved`<br>• `fcr_score` |
| **2. EFFICIENCY / Service Timeliness** | How fast and efficient was the service? | • `first_response_time`<br>• `average_response_time` <br>• `average_handling_time` |
| **3. EFFORT / Customer Ease** | How simple was the process for the customer? | • `customer_ease_score` (inferred CES) |
| **4. EMPATHY / Interaction Quality** | What was the emotional tone of the interaction? | • `sentiment_score`<br>• `sentiment_shift` |

#### **Calculation Flow:**

1.  **Micro-Metric Scoring:** For each conversation, the system calculates all 7 micro-metrics.
    *   *AI-Derived:* `resolution_achieved`, `fcr_score`, `customer_ease`, `sentiment_score`, `sentiment_shift`.
    *   *Objectively Calculated:* `first_response_time`, `average_response_time`, `average_handling_time`.
    *   All scores are normalized to a **1-10 scale**.

2.  **Pillar Score Calculation:** The micro-metrics are combined to form the four Pillar Scores.
    *   `EFFECTIVENESS / Resolution Quality Score` = (`resolution_achieved` + `fcr_score`) / 2
    *   `EFFICIENCY / Service Timeliness Score` = (`first_response_time_score` + `avg_response_time_score`) / 2
    *   `EFFORT / Customer Ease Score` = `customer_ease_score`
    *   `EMPATHY / Interaction Quality Score` = (`sentiment_score` \* 0.4) + (`sentiment_shift` \* 0.6)

3.  **Final CSI Score Calculation:** The four Pillar Scores are combined in a weighted average to produce the final CSI.
    *   **CSI = (`Resolution Quality` \* 0.40) + (`Customer Ease` \* 0.25) + (`Interaction Quality` \* 0.20) + (`Service Timeliness` \* 0.15)**

#### **Benefits of the New Approach:**

*   **Diagnostic Power:** If the CSI score drops, you can immediately see which pillar is responsible. A low `Resolution Quality` score points to training or knowledge gaps, while a low `Service Timeliness` score indicates staffing or efficiency issues.
*   **Holistic View:** The CSI provides a balanced view of performance, preventing agents from optimizing for one metric (like speed) at the expense of others (like resolution).
*   **Actionable Insights:** Each pillar directly maps to business actions: improve agent training (Resolution), optimize workflows (Ease), enhance soft skills (Interaction), or adjust staffing (Timeliness).
*   **Objective and Reliable:** By breaking down satisfaction into smaller, more specific components, the AI's task becomes more focused and the final score more reliable and less of a "black box."

---

### **3. Implementation Overview**

The transition will be managed in a series of planned phases:
1.  **Schema Overhaul:** Update the database to store the new CSI and pillar scores.
2.  **Logic Refactoring:** Update the AI service and core processing logic to calculate the new metrics.
3.  **API & Analytics Update:** Expose the new, richer data through the API for dashboard consumption.

This strategic evolution will transform the PowerPulse platform from a simple reporting tool into a powerful business intelligence engine for driving customer satisfaction.
