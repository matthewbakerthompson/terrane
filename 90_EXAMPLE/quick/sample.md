# Card payments, as the team documented it

The two diagrams the team keeps in its README, read together as one sketch:
the systems a flowchart draws and the participants a sequence diagram names
are the same records, so the picture of where things run and the picture of
what happens in what order come from one model.

## Where things run

```mermaid
flowchart LR
  subgraph Channels
    mobile[Cardholder mobile app]
  end
  subgraph Core banking
    auth[Authorization switch]
    ledger[(Card ledger)]
    statements[Statement service]
  end
  mobile -->|HTTPS| statements
  auth -->|MQ| ledger
  ledger -->|FileTransfer| statements
```

## How an authorization goes

```mermaid
sequenceDiagram
  actor merchant as Merchant
  participant auth as Authorization switch
  participant fraud as Fraud scoring
  participant ledger as Card ledger
  merchant->>auth: Presents a transaction
  auth->>fraud: Score the transaction
  fraud-->>auth: Score
  auth->>ledger: Post the authorization
  Note over auth: under 500ms end to end
```

A third block the reader cannot take is said and left out, and the rest still
come through:

```mermaid
classDiagram
  Account <|-- SavingsAccount
```
