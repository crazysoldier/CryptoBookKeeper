# Crypto Normalizer - Data Dictionary

## Übersicht

Dieses Data Dictionary beschreibt alle Datenfelder, die im Crypto Normalizer System verwendet werden. Es definiert die einheitlichen Schemata für Exchange- und On-Chain-Daten sowie das finale Unified Transaction Model.

## Raw Data Schemas

### Exchange Data Schema

#### Trades Table
| Feld | Typ | Beschreibung | Beispiel | Constraints |
|------|-----|--------------|----------|-------------|
| `source` | VARCHAR | Exchange-Name | "binance" | NOT NULL |
| `exchange` | VARCHAR | Exchange-Identifier | "binance" | NOT NULL |
| `account` | VARCHAR | Account-Identifier | "main" | NOT NULL |
| `txid` | VARCHAR | Eindeutige Transaktions-ID | "12345" | NOT NULL, UNIQUE |
| `orderid` | VARCHAR | Order-ID | "67890" | NULLABLE |
| `datetime` | TIMESTAMP | UTC-Zeitstempel | "2023-01-01T12:00:00Z" | NOT NULL |
| `base` | VARCHAR | Basis-Asset | "BTC" | NOT NULL |
| `quote` | VARCHAR | Quote-Asset | "USDT" | NOT NULL |
| `side` | VARCHAR | Transaktions-Seite | "buy", "sell" | NOT NULL |
| `amount` | DECIMAL(38,18) | Transaktionsmenge | 0.001 | NOT NULL, > 0 |
| `price` | DECIMAL(38,18) | Preis | 45000.00 | NOT NULL, > 0 |
| `fee_currency` | VARCHAR | Gebühren-Währung | "USDT" | NULLABLE |
| `fee_amount` | DECIMAL(38,18) | Gebührenbetrag | 0.50 | NULLABLE, >= 0 |
| `address` | VARCHAR | Adresse (bei P2P) | "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" | NULLABLE |
| `status` | VARCHAR | Transaktions-Status | "closed" | NOT NULL |
| `raw_json` | JSON | Rohdaten der API | `{"id": "12345"}` | NOT NULL |

#### Deposits Table
| Feld | Typ | Beschreibung | Beispiel | Constraints |
|------|-----|--------------|----------|-------------|
| `source` | VARCHAR | Exchange-Name | "binance" | NOT NULL |
| `exchange` | VARCHAR | Exchange-Identifier | "binance" | NOT NULL |
| `account` | VARCHAR | Account-Identifier | "main" | NOT NULL |
| `txid` | VARCHAR | Eindeutige Transaktions-ID | "dep_12345" | NOT NULL, UNIQUE |
| `orderid` | VARCHAR | Order-ID | NULL | NULLABLE |
| `datetime` | TIMESTAMP | UTC-Zeitstempel | "2023-01-01T12:00:00Z" | NOT NULL |
| `base` | VARCHAR | Asset | "BTC" | NOT NULL |
| `quote` | VARCHAR | Quote-Asset | NULL | NULLABLE |
| `side` | VARCHAR | Transaktions-Seite | "deposit" | NOT NULL |
| `amount` | DECIMAL(38,18) | Transaktionsmenge | 0.001 | NOT NULL, > 0 |
| `price` | DECIMAL(38,18) | Preis | NULL | NULLABLE |
| `fee_currency` | VARCHAR | Gebühren-Währung | "BTC" | NULLABLE |
| `fee_amount` | DECIMAL(38,18) | Gebührenbetrag | 0.0001 | NULLABLE, >= 0 |
| `address` | VARCHAR | Absender-Adresse | "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" | NULLABLE |
| `status` | VARCHAR | Transaktions-Status | "completed" | NOT NULL |
| `raw_json` | JSON | Rohdaten der API | `{"id": "dep_12345"}` | NOT NULL |

#### Withdrawals Table
| Feld | Typ | Beschreibung | Beispiel | Constraints |
|------|-----|--------------|----------|-------------|
| `source` | VARCHAR | Exchange-Name | "binance" | NOT NULL |
| `exchange` | VARCHAR | Exchange-Identifier | "binance" | NOT NULL |
| `account` | VARCHAR | Account-Identifier | "main" | NOT NULL |
| `txid` | VARCHAR | Eindeutige Transaktions-ID | "wth_12345" | NOT NULL, UNIQUE |
| `orderid` | VARCHAR | Order-ID | NULL | NULLABLE |
| `datetime` | TIMESTAMP | UTC-Zeitstempel | "2023-01-01T12:00:00Z" | NOT NULL |
| `base` | VARCHAR | Asset | "BTC" | NOT NULL |
| `quote` | VARCHAR | Quote-Asset | NULL | NULLABLE |
| `side` | VARCHAR | Transaktions-Seite | "withdrawal" | NOT NULL |
| `amount` | DECIMAL(38,18) | Transaktionsmenge | 0.001 | NOT NULL, > 0 |
| `price` | DECIMAL(38,18) | Preis | NULL | NULLABLE |
| `fee_currency` | VARCHAR | Gebühren-Währung | "BTC" | NULLABLE |
| `fee_amount` | DECIMAL(38,18) | Gebührenbetrag | 0.0001 | NULLABLE, >= 0 |
| `address` | VARCHAR | Empfänger-Adresse | "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" | NOT NULL |
| `status` | VARCHAR | Transaktions-Status | "completed" | NOT NULL |
| `raw_json` | JSON | Rohdaten der API | `{"id": "wth_12345"}` | NOT NULL |

### On-Chain Data Schema

#### Token Transfers Table
| Feld | Typ | Beschreibung | Beispiel | Constraints |
|------|-----|--------------|----------|-------------|
| `tx_hash` | VARCHAR | Transaction Hash | "0x123..." | NOT NULL |
| `log_index` | INTEGER | Log Index | 0 | NOT NULL |
| `contract_address` | VARCHAR | Contract Address | "0xA0b86a33E6..." | NULLABLE |
| `from_address` | VARCHAR | Absender-Adresse | "0x123..." | NOT NULL |
| `to_address` | VARCHAR | Empfänger-Adresse | "0x456..." | NOT NULL |
| `value` | DECIMAL(38,18) | Transfer-Wert | 1000.0 | NOT NULL, >= 0 |
| `token_symbol` | VARCHAR | Token-Symbol | "USDC" | NULLABLE |
| `token_decimal` | INTEGER | Token-Dezimalstellen | 6 | NULLABLE |
| `block_number` | BIGINT | Block-Nummer | 18500000 | NOT NULL |
| `block_timestamp` | TIMESTAMP | Block-Zeitstempel | "2023-01-01T12:00:00Z" | NOT NULL |
| `chain` | VARCHAR | Chain-Name | "ethereum" | NOT NULL |
| `raw_json` | JSON | Rohdaten | `{"logIndex": 0}` | NOT NULL |

#### Transaction Receipts Table
| Feld | Typ | Beschreibung | Beispiel | Constraints |
|------|-----|--------------|----------|-------------|
| `tx_hash` | VARCHAR | Transaction Hash | "0x123..." | NOT NULL, UNIQUE |
| `block_number` | BIGINT | Block-Nummer | 18500000 | NOT NULL |
| `block_timestamp` | TIMESTAMP | Block-Zeitstempel | "2023-01-01T12:00:00Z" | NOT NULL |
| `from_address` | VARCHAR | Absender-Adresse | "0x123..." | NOT NULL |
| `to_address` | VARCHAR | Empfänger-Adresse | "0x456..." | NOT NULL |
| `value` | DECIMAL(38,18) | ETH-Wert | 1.5 | NOT NULL, >= 0 |
| `gas_used` | BIGINT | Verwendetes Gas | 21000 | NOT NULL |
| `gas_price` | DECIMAL(38,18) | Gas-Preis | 0.00000002 | NOT NULL |
| `status` | INTEGER | Transaktions-Status | 1 | NOT NULL |
| `chain` | VARCHAR | Chain-Name | "ethereum" | NOT NULL |
| `raw_json` | JSON | Rohdaten | `{"status": 1}` | NOT NULL |

## Unified Transaction Schema

### Transactions Unified Table
| Feld | Typ | Beschreibung | Beispiel | Constraints |
|------|-----|--------------|----------|-------------|
| `domain` | VARCHAR | Datenquelle | "exchange", "onchain" | NOT NULL |
| `source` | VARCHAR | Spezifische Quelle | "binance", "ethereum" | NOT NULL |
| `ts_utc` | TIMESTAMP | UTC-Zeitstempel | "2023-01-01T12:00:00Z" | NOT NULL |
| `txid` | VARCHAR | Eindeutige Transaktions-ID | "12345", "0x123..." | NOT NULL, UNIQUE |
| `base` | VARCHAR | Basis-Asset | "BTC", "ETH" | NULLABLE |
| `quote` | VARCHAR | Quote-Asset | "USDT", "USD" | NULLABLE |
| `side` | VARCHAR | Transaktions-Seite | "buy", "sell", "deposit", "withdrawal", "transfer" | NOT NULL |
| `amount` | DECIMAL(38,18) | Transaktionsmenge | 0.001 | NOT NULL, > 0 |
| `price` | DECIMAL(38,18) | Preis (bei Trades) | 45000.00 | NULLABLE, > 0 |
| `fee_ccy` | VARCHAR | Gebühren-Währung | "USDT", "ETH" | NULLABLE |
| `fee_amt` | DECIMAL(38,18) | Gebührenbetrag | 0.50 | NULLABLE, >= 0 |
| `addr_from` | VARCHAR | Absender-Adresse | "1A1z...", "0x123..." | NULLABLE |
| `addr_to` | VARCHAR | Empfänger-Adresse | "1B2y...", "0x456..." | NULLABLE |
| `chain` | VARCHAR | Blockchain-Name | "ethereum", "polygon" | NULLABLE |
| `token_symbol` | VARCHAR | Token-Symbol | "USDC", "USDT" | NULLABLE |
| `token_decimal` | INTEGER | Token-Dezimalstellen | 6, 18 | NULLABLE |
| `raw_json` | JSON | Rohdaten | `{"id": "12345"}` | NOT NULL |

## Datenqualitäts-Regeln

### Allgemeine Regeln
1. **NOT NULL Constraints**: Alle kritischen Felder müssen Werte haben
2. **UNIQUE Constraints**: Transaktions-IDs müssen eindeutig sein
3. **Range Constraints**: Beträge müssen positiv sein
4. **Format Constraints**: Zeitstempel müssen UTC sein

### Exchange-spezifische Regeln
1. **Trades**: `base` und `quote` müssen gesetzt sein
2. **Deposits/Withdrawals**: `side` muss "deposit" oder "withdrawal" sein
3. **Gebühren**: `fee_amount` muss >= 0 sein

### On-Chain-spezifische Regeln
1. **Transfers**: `from_address` und `to_address` müssen gesetzt sein
2. **Token-Daten**: `token_decimal` muss zwischen 0 und 18 liegen
3. **Block-Daten**: `block_number` muss positiv sein

## Zeitstempel-Handling

### UTC-Normalisierung
- Alle Zeitstempel werden auf UTC normalisiert
- Format: ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`)
- Zeitzone-Information wird nicht gespeichert

### Zeitstempel-Quellen
- **Exchange**: API-spezifische Formate → UTC
- **On-Chain**: Block-Timestamps → UTC
- **Unified**: Einheitliches UTC-Format

## Währungs-Handling

### Asset-Identifikation
- **Exchange**: Standard-Symbole (BTC, ETH, USDT)
- **On-Chain**: Contract-Adressen + Symbol-Mapping
- **Unified**: Einheitliche Symbol-Liste

### Dezimalstellen
- **Exchange**: API-spezifische Genauigkeit
- **On-Chain**: Token-Contract-Definition
- **Unified**: Maximale Genauigkeit (18 Dezimalstellen)

## Metadaten

### Raw JSON
- Vollständige API-Antworten
- Für Debugging und erweiterte Analysen
- JSON-Format für Flexibilität

### Audit-Trail
- Export-Zeitstempel
- API-Version
- Verarbeitungs-Status

## Indexierung

### Performance-Indizes
```sql
-- Zeitstempel-Index für Zeitbereichsabfragen
CREATE INDEX idx_ts_utc ON transactions_unified(ts_utc);

-- Domain/Source-Index für Quellen-Filter
CREATE INDEX idx_domain_source ON transactions_unified(domain, source);

-- Asset-Index für Asset-spezifische Abfragen
CREATE INDEX idx_base_quote ON transactions_unified(base, quote);
```

### Partitionierung
```sql
-- Zeitbasierte Partitionierung
PARTITION BY (year(ts_utc), month(ts_utc))
```

## Datenvalidierung

### dbt-Tests
```sql
-- NOT NULL Tests
SELECT * FROM {{ ref('transactions_unified') }}
WHERE txid IS NULL

-- UNIQUE Tests
SELECT txid, COUNT(*) as count
FROM {{ ref('transactions_unified') }}
GROUP BY txid
HAVING COUNT(*) > 1

-- Range Tests
SELECT * FROM {{ ref('transactions_unified') }}
WHERE amount <= 0
```

### Business-Logic-Tests
```sql
-- Trades müssen Preis haben
SELECT * FROM {{ ref('transactions_unified') }}
WHERE side IN ('buy', 'sell') AND price IS NULL

-- Deposits/Withdrawals dürfen keinen Preis haben
SELECT * FROM {{ ref('transactions_unified') }}
WHERE side IN ('deposit', 'withdrawal') AND price IS NOT NULL
```
