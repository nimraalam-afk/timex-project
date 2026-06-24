# Architecture Diagram

```mermaid
flowchart TD
    A[Collector Profile] --> B[Orchestrator]
    B --> C[Marketplace Provider Fetch Tool]
    C --> D[Preference Filter + Validation]
    D --> E[Recommender Agent]
    E --> F[Evaluator Agent]
    F --> G[Recommendations UI]

    A -. provides constraints .-> D
    A -. provides taste examples .-> E
    F -. blocks or flags issues .-> G