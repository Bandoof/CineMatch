# Architecture / Архітектура v1.4

```mermaid
flowchart TD
    Local[Local Streamlit entry<br/>app/streamlit_app.py] --> UI[Cinematic product UI<br/>app/product_ui.py]
    Demo[Portfolio entry<br/>app/portfolio_app.py] --> UI
    UI --> Actions[Library actions / Undo<br/>profile validation schemas 2–6]
    Actions --> LocalGate{Local mode?}
    LocalGate -->|yes| SQLite[SQLite CAS memory / named profiles<br/>local JSON import & export]
    LocalGate -->|portfolio| Visitor[Visitor session state<br/>synthetic seed / reset / own JSON export]
    UI --> Facade[CatalogView<br/>identity mapping / exact dedup / source provenance]
    UI --> Search[Session-owned indexed multilingual search]
    Search --> Facade
    Facade --> Historical[Original Recommender<br/>seven modes / MF / item KNN / genres / popularity]
    Facade --> Heuristics[Modern metadata heuristics<br/>genre affinity / attributed available ratings]
    Historical --> LocalData[Public MovieLens development data<br/>local numerical artifacts]
    Historical --> DemoPack[Optional bounded public demo pack<br/>own engine and LRU per visitor]
    Facade --> Catalog[Immutable dated metadata snapshot<br/>provider IDs and source links]
    Catalog --> Sample[Credential-free sample<br/>Wikidata CC0 / TVmaze CC BY-SA]
    Refresh[Explicit local refresh / CLI<br/>bounded requests / timeout / rate limits] --> Cache[Metadata response cache<br/>offline reads / retrieval timestamps]
    Cache --> Catalog
    Refresh --> TV[TVmaze public series API]
    Refresh --> Wiki[Wikidata labels and structured statements]
    Refresh --> TMDB[Optional TMDB<br/>environment credential / no offline dependency]
    Research[Offline research scripts<br/>train / validation / frozen evidence integrity] --> Evidence[Archived research reports / manifests<br/>historical claims and limitations]
    Research --> Embeddings[Optional cached MiniLM<br/>TF-IDF + LSA artifacts]
    Embeddings -. explicitly attached local artifacts .-> Historical
    UI --> Lab[Research UI<br/>original results / explanations / limitations]
    Evidence --> Lab
```

The historical engine's numerical formulas and production Adaptive default are
unchanged. Its scores cover its known MovieLens identities. Modern metadata
never creates training observations. Semantic without an attached text artifact
falls back to genres; Adaptive without a learned mixing policy falls back to
community quality for films. These conditions are visible in For You.

Portfolio mode never constructs SQLite/profile stores or provider clients. It
uses the committed 30-title dated snapshot and, if explicitly prepared, its own
bounded public development pack. The original global profile LRU is rebound to
each visitor with the same underlying formula. The index and mutable preferences
are session-owned. Provider response caches belong to explicit local operations,
not anonymous visitors. Optional artwork is fetched by the browser from TVmaze;
no visitor preference or query is sent to that provider by the demo server.

Українською: Streamlit керує інтерфейсом; CatalogView узгоджує ідентичності, але
не змінює навчальні оцінки. Локальний режим зберігає профілі через SQLite/CAS.
Демонстрація тримає лише синтетичний стан поточної сесії й окремий кеш результатів.
MovieLens залишається історичною ML-базою; нові назви — метадані й явно позначені
евристики. Дослідницький pipeline незалежний від показу, його докази не переписано.

This diagram describes the implemented candidate, not a deployed multiuser
service. Hosting security and admission limits remain platform/operator work.
