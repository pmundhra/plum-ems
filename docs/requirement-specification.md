### Design Challenge: 
Endorsement Management System for Group Insurance Business Context: At the start of every year, an employer purchases group insurance for all employees and their dependents. The premium is based on the employee count and age bands at purchase time. Throughout the year, changes to employee status (additions, deletions, updates) require “endorsements” that must be executed by the insurer. Endorsements can be processed via real-time or batch APIs. Each endorsement is only effective after insurer confirmation. To execute endorsements, the employer maintains an Endorsement Account (EA) with the insurer. Funds must be sufficient for each new addition; excess funds from deletions are credited back. 

### Candidate Task: 
- Design, develop, and (preferred) demo an Endorsement Management System that:
- Executes endorsements in either real-time or batch, as defined by the insurer.
- Ensures employees receive uninterrupted coverage from the moment they are eligible—no gaps in medical cover.
- Optimizes endorsement processing so employers can maintain a minimum required balance in their endorsement account.
- Provides real-time visibility to stakeholders about endorsement execution status, including account balance, outstanding items, and errors.
- Utilizes AI/automation tools wherever appropriate (e.g., process optimization, anomaly detection, reconciliation, prediction).
- Is architected for scalability (100K employers, average 10 employee changes per employer per day, 10 different insurance providers). 

### Assumptions: 
- Insurer provides batch and real-time APIs for endorsement processing. 
- Insurer can process one batch at a time, will have a varying SLAs for batch (few hours to few days) 
- Endorsement failures must be handled with retries and clear error communication. 
- Real-time insight, notifications, and automated reconciliation are required. Deliverables: 
- High-level architecture and system components (illustrated). 
- Approach for ensuring no loss of coverage at any stage. 
- Algorithm or approach for minimizing EA balance requirements. 
- User flows or example screens/dashboards for real-time visibility. 
- How AI/automation is leveraged (describe or demo). 
- Code/prototype (demo if time allows). 

### Timeframe: 
You have one week to complete and demo your solution. Use any suitable technologies or AI tools as needed.

