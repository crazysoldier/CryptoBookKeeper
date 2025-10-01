# CryptoBookKeeper - Projektübersicht

**Version 0.1.0** - Transaction Normalization Stage

## Projektziel

**CryptoBookKeeper** ist eine umfassende Kryptowährungs-Buchhaltungsanwendung, die derzeit in der Phase der Daten-Normalisierung steht. Das System normalisiert Transaktionsdaten aus verschiedenen Quellen in ein einheitliches, analysierbares Format und soll zu einer vollständigen Buchhaltungslösung ausgebaut werden.

## Hauptfunktionen

### 1. Multi-Source Data Export
- **Exchange-Daten**: Automatischer Export von Trades, Deposits und Withdrawals über CCXT
- **On-Chain-Daten**: EVM-basierte Token-Transfers und Receipts via web3.py
- **Unified Schema**: Einheitliches Datenmodell für alle Transaktionsquellen

### 2. Datenverarbeitung
- **DuckDB**: In-Process OLAP-Datenbank für schnelle Analysen
- **Parquet**: Spaltenorientiertes Storage-Format für Effizienz
- **dbt**: Datenmodellierung und Transformationen

### 3. Orchestrierung
- **Makefile**: Reproduzierbare Pipeline-Ausführung
- **Environment Management**: Konfigurierbare API-Keys und Parameter
- **Error Handling**: Robuste Fehlerbehandlung und Retry-Logik

## Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Exchanges     │    │   Blockchain    │    │   Data Lake     │
│   (CCXT APIs)   │    │   (web3.py)     │    │   (DuckDB)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Raw Data Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Exchanges   │  │ On-Chain    │  │ Metadata    │           │
│  │ (CSV)       │  │ (CSV)       │  │ (JSON)      │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Staging Layer (DuckDB)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Type Safety │  │ Normalize   │  │ Partition   │           │
│  │ & Casting   │  │ Timestamps  │  │ by Date     │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                Curated Layer (Parquet)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Unified     │  │ Optimized   │  │ Analytics   │           │
│  │ Schema      │  │ Storage     │  │ Ready       │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 dbt Models                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Raw Models  │  │ Staging     │  │ Curated     │           │
│  │ (Sources)   │  │ (Transform) │  │ (Business)  │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Technologie-Stack

### Core Technologies
- **Python 3.11+**: Hauptprogrammiersprache
- **DuckDB**: In-Process OLAP-Datenbank
- **Parquet**: Spaltenorientiertes Storage-Format
- **dbt**: Datenmodellierung und Tests

### Data Sources
- **CCXT**: Exchange-API-Integration (100+ Exchanges)
- **web3.py**: Ethereum und EVM-Chain-Integration
- **RPC-Endpoints**: Blockchain-Datenabfragen

### Data Processing
- **Polars**: Schnelle Datenverarbeitung
- **PyArrow**: Parquet-Integration
- **pandas**: Datenmanipulation (falls benötigt)

### Development Tools
- **dbt-core & dbt-duckdb**: Datenmodellierung
- **ruff**: Code-Qualität
- **pre-commit**: Git-Hooks
- **tqdm**: Progress-Bars

## Projektstruktur

```
crypto-normalizer-minimal/
├── project-docs/              # Projektdokumentation
│   ├── overview.md            # Diese Datei
│   ├── requirements.md         # Anforderungen
│   ├── tech-specs.md          # Technische Spezifikationen
│   └── data-dictionary.md     # Datenmodell-Dokumentation
├── data/                      # Datenverzeichnis
│   ├── raw/                   # Rohdaten
│   │   ├── exchanges/         # Exchange-CSVs
│   │   └── onchain/          # On-Chain-CSVs
│   └── curated/              # Normalisierte Parquet-Daten
├── scripts/                   # Python-Scripts
│   ├── export_exchanges.py    # Exchange-Export
│   ├── export_onchain_eth.py  # On-Chain-Export
│   └── stage_duckdb.py        # DuckDB-Staging
├── sql/                       # SQL-Scripts
│   └── duckdb_init.sql        # DuckDB-Initialisierung
├── dbt/                       # dbt-Projekt
│   ├── dbt_project.yml        # dbt-Konfiguration
│   ├── models/                # dbt-Modelle
│   │   ├── raw/               # Raw-Modelle
│   │   └── curated/           # Curated-Modelle
│   └── seeds/                 # dbt-Seeds
├── .env.template              # Umgebungsvariablen-Vorlage
├── .gitignore                 # Git-Ignore
├── Makefile                   # Orchestrierung
├── README.md                   # Hauptdokumentation
└── requirements.txt            # Python-Dependencies
```

## Workflow

### 1. Setup Phase
```bash
make setup                    # venv + dependencies
cp .env.template .env         # Konfiguration
# .env editieren              # API-Keys eintragen
```

### 2. Data Export Phase
```bash
make export-exchanges         # Exchange-Daten exportieren
make export-eth              # On-Chain-Daten exportieren
```

### 3. Data Processing Phase
```bash
make stage                   # DuckDB-Staging
make dbt                     # dbt-Transformationen
```

### 4. Analysis Phase
```bash
# Datenanalyse in DuckDB oder über dbt
# Beispielberichte generieren
```

## Vorteile

### Für Entwickler
- **Minimal Setup**: Schneller Einstieg in Crypto-Datenanalyse
- **Reproduzierbar**: Vollständig automatisierte Pipeline
- **Erweiterbar**: Modulare Architektur für neue Features

### Für Analysten
- **Unified Schema**: Einheitliche Sicht auf alle Transaktionen
- **Performance**: DuckDB + Parquet für schnelle Analysen
- **Flexibilität**: SQL-basierte Abfragen und dbt-Modelle

### Für Unternehmen
- **Compliance**: Vollständige Transaktionshistorie
- **Audit-Trail**: Nachvollziehbare Datenverarbeitung
- **Skalierbar**: Von Einzelperson bis Enterprise

## Nächste Schritte

1. **Konfiguration**: `.env`-Datei mit API-Keys ausfüllen
2. **Test-Export**: Kleine Datenmenge testen
3. **Anpassung**: Pipeline für spezifische Anforderungen erweitern
4. **Monitoring**: Logs und Metriken implementieren
5. **Visualisierung**: Dashboard oder Reports hinzufügen

## Support

- **Dokumentation**: Siehe `project-docs/` für Details
- **Issues**: GitHub Issues für Bug-Reports
- **Community**: Diskussionen und Feature-Requests
