# Docling Parsing Pipeline (Section 2.3)

Two diagrams for the chapter. The first shows the pipeline as built. The second shows what actually happened when the pipeline was tested against a real Citi credit card statement, which is the failure case described in the text.

## How a statement flows through the pipeline

```mermaid
flowchart TD
    A[Bank or card statement PDF] --> B[Docling DocumentConverter]
    B --> C{Any tables detected?}
    C -- No --> Z[Raise: no tables found]
    C -- Yes --> D[Dedupe column names per table]
    D --> E[Pick the largest table as the likely ledger]
    E --> F[Keep only rows with a dollar-amount cell]
    F --> G[Count MM/DD date markers in the raw PDF text]
    G --> H{Row count matches date marker count?}
    H -- Yes --> I[Save transactions to CSV]
    H -- No --> J[Print warning: rows may be dropped or merged]
    J --> I
```

The date-marker count in step G comes from a second, independent pass over the PDF's text layer using `pypdf`. It doesn't rely on Docling's table model at all, which is the point: if the table model silently drops or merges a row, this check has a chance to catch it because it never touches the table object in the first place.

## What happened on the real test statement

Against a synthetic sample statement, this pipeline works cleanly end to end. Against a real six-page Citi credit card statement, it extracted 13 of 14 transactions correctly. Here is why:

```mermaid
flowchart LR
    subgraph Page 3 of the statement
        H1["Two-line column header:
'Sale' / 'Date'
then 'Post' / 'Date'"]
        R1["08/03 08/03 PIZZA HUT ... $13.78"]
        R2["08/06 08/06 PARK'N GO RIC AIRPORT ... $52.00"]
    end

    H1 -->|misread as extra data rows| M1[Table-structure model merges
the header, ledger, and the
fee/interest section into one table]
    R1 -->|row dropped during structure detection| M2[Missing from output entirely]
    R2 -->|cells misaligned| M3["Description collapsed to just 'VA'"]
    M1 --> OUT[CSV: 13 of 14 transactions,
one row corrupted, no error raised]
    M2 --> OUT
    M3 --> OUT
```

The text layer of the PDF was intact for both rows, this was not a text-extraction failure. Docling's table-structure model drew the grid lines wrong on a dense, multi-section page, and neither Docling nor the parsing script raised an error. Nothing in the output looked broken unless you counted rows by hand against the source PDF. That silent-failure quality is the reason the row-count cross-check in the diagram above exists: catching this kind of miss requires checking the tool's output against something the tool itself didn't produce.
