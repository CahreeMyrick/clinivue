# Example Prompts

## 1. Medical Professionals & Aspiring Professionals

| Prompt | Primary Intent / Structure |
|---|---|
| What findings on this chest X-ray are most clinically significant? | Image interpretation, prioritization |
| Which findings support pulmonary edema, and which findings argue against it? | Evidence-for / evidence-against |
| Compare the radiographic features of cardiogenic pulmonary edema and multifocal pneumonia. | Differential comparison |
| What conditions are associated with bilateral pleural effusions and cardiomegaly? | Multi-entity relational reasoning |
| What is the significance of a new unilateral pleural effusion in this patient? | Finding → clinical significance |
| What additional imaging or tests are commonly considered after this finding? | Finding → next-step retrieval |
| Show me the evidence connecting this radiographic finding to heart failure. | Explicit evidence / provenance request |
| What alternative explanations should be considered for this opacity? | Differential generation |
| Is the endotracheal tube appropriately positioned? | Device localization / spatial reasoning |
| What anatomical region contains the abnormality highlighted here? | Anatomy localization |
| What relationships exist between cardiomegaly, pulmonary edema, and pleural effusion? | Knowledge-graph traversal |
| Find similar chest X-rays with the same combination of findings. | Multimodal retrieval |
| Summarize current guideline-supported evaluation of exertional chest pain. | Text-only RAG |
| What evidence supports using CT after an indeterminate pulmonary opacity on chest radiography? | Procedure justification |
| A patient has chest pain with exertion but a normal chest X-ray. What conditions remain relevant? | Negative evidence + reasoning |
| Explain why this image could represent atelectasis rather than consolidation. | Fine-grained distinction |
| Which findings here are direct visual observations, and which are inferred clinical concepts? | Interpretability / ontology distinction |
| Walk me through how you would interpret this chest X-ray systematically. | Educational workflow |
| Why does cardiomegaly appear enlarged on a PA chest X-ray? | Mechanistic explanation |
| What is the difference between pleural effusion and pulmonary edema on chest X-ray? | Concept comparison |
| What anatomy should I identify first when reading a chest X-ray? | Educational anatomy |
| Give me the reasoning chain from this image finding to the possible associated conditions. | Explicit reasoning path |
| Quiz me on the findings visible in this image. | Interactive education |

## 2. Average Person

| Prompt | Primary Intent / Structure |
|---|---|
| What does this chest X-ray show in plain English? | Simplification |
| What does "pleural effusion" mean? | Definition |
| Why have I been getting chest pain while running? | Symptom explanation |
| Could chest pain during exercise be related to my lungs or my heart? | Broad differential |
| What are some reasons someone might feel short of breath during exercise? | Symptom exploration |
| What does it mean if an X-ray report says "cardiomegaly"? | Report interpretation |
| My report says "mild bibasilar atelectasis." What does that mean? | Medical language translation |
| Is a small pleural effusion always serious? | Risk interpretation |
| What questions should I ask my doctor about this X-ray result? | Decision support / preparation |
| What symptoms would make chest pain more concerning? | Safety / escalation |
| Why might a doctor order a CT scan after a chest X-ray? | Procedure explanation |
| Can a chest X-ray tell if I have pneumonia? | Capability / limitation |
| If my X-ray is normal, can I still have a heart or lung problem? | Negative-result interpretation |
| Can you explain this report without medical jargon? | Summarization / simplification |
| What’s the difference between pneumonia, fluid in the lungs, and fluid around the lungs? | Multi-concept comparison |
| What could cause chest pain that only happens when I exercise? | Trigger-conditioned symptom reasoning |
| What does this image finding mean, and what evidence supports that explanation? | Evidence-aware explanation |

## Prompt Characteristics Covered

These prompts exercise a range of system behaviors:

- **Entity extraction**
  - chest pain
  - running
  - pleural effusion
  - cardiomegaly

- **Relation extraction**
  - `ChestPain --OCCURS_DURING--> PhysicalExertion`

- **Image grounding**
  - "Where is the abnormality?"

- **Knowledge-graph traversal**
  - "What relationships exist between cardiomegaly, edema, and effusion?"

- **Differential reasoning**
  - "What else could explain this opacity?"

- **RAG / evidence retrieval**
  - "What guidelines support the next step?"

- **Interpretability**
  - "Why did you return this condition?"

- **Negative evidence**
  - "What remains relevant if the X-ray is normal?"

- **Education**
  - "Walk me through this systematically."

- **Plain-language translation**
  - "Explain this report without jargon."

- **Action-oriented support**
  - "What questions should I ask my doctor?"

- **Multimodal retrieval**
  - "Find similar cases."

## Evaluation Note

A useful benchmark should include both:

- **Single-entity queries**
- **Multi-entity relational queries**

The multi-entity queries are especially important because they are where the knowledge graph should provide the most value over ordinary vector-only RAG.
