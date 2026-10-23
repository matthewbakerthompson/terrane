# Value Streams

How the organization delivers something a customer or partner wants, as a sequence of stages, each with the condition that must be met to move on. A stage named after a department usually means the stream has turned back into an org chart.

```mermaid
%%{init: {'flowchart': {'curve': 'basis'}} }%%
flowchart LR
  %% Value Streams
  %% Generated from the model by `terrane render`. Do not edit by hand.

  subgraph grp_Client_Opportunity_to_Live_Program["Client Opportunity to Live Program"]
    direction TB
    VS_ONBOARD_CLIENT_S01["Qualify Opportunity"]
    VS_ONBOARD_CLIENT_S02["Diligence & Contract"]
    VS_ONBOARD_CLIENT_S03["Design Program"]
    VS_ONBOARD_CLIENT_S04["Configure Platform"]
    VS_ONBOARD_CLIENT_S05["Convert Portfolio"]
    VS_ONBOARD_CLIENT_S06["Stabilize"]
    VS_ONBOARD_CLIENT_S07["Steady-State Service"]
  end

  subgraph grp_Concept_to_Market["Concept to Market"]
    direction TB
    VS_LAUNCH_PRODUCT_S01["Concept & Business Case"]
    VS_LAUNCH_PRODUCT_S02["Design & Price"]
    VS_LAUNCH_PRODUCT_S03["Legal & Compliance Review"]
    VS_LAUNCH_PRODUCT_S04["Configure & Test"]
    VS_LAUNCH_PRODUCT_S05["Launch"]
    VS_LAUNCH_PRODUCT_S06["Monitor & Iterate"]
  end

  subgraph grp_Dealer_Purchase_to_Funded_Loan["Dealer Purchase to Funded Loan"]
    direction TB
    VS_FINANCE_PURCHASE_S01["Dealer Submits"]
    VS_FINANCE_PURCHASE_S02["Decision & Terms"]
    VS_FINANCE_PURCHASE_S03["Docs & Stipulations"]
    VS_FINANCE_PURCHASE_S04["Board & Fund Dealer"]
    VS_FINANCE_PURCHASE_S05["Perfect Lien"]
    VS_FINANCE_PURCHASE_S06["Service Loan"]
    VS_FINANCE_PURCHASE_S07["Payoff or Recover"]
  end

  subgraph grp_Delinquency_to_Recovery["Delinquency to Recovery"]
    direction TB
    VS_RECOVER_VALUE_S01["Detect Delinquency"]
    VS_RECOVER_VALUE_S02["Segment & Strategize"]
    VS_RECOVER_VALUE_S03["Contact & Treat"]
    VS_RECOVER_VALUE_S04["Arrange or Assist"]
    VS_RECOVER_VALUE_S05["Charge Off"]
    VS_RECOVER_VALUE_S06["Place or Sell"]
    VS_RECOVER_VALUE_S07["Recover & Account"]
  end

  subgraph grp_Deposit_Opened_to_Maturity["Deposit Opened to Maturity"]
    direction TB
    VS_GROW_SAVINGS_S01["Choose Product"]
    VS_GROW_SAVINGS_S02["Open & Verify"]
    VS_GROW_SAVINGS_S03["Fund"]
    VS_GROW_SAVINGS_S04["Accrue & Report"]
    VS_GROW_SAVINGS_S05["Mature or Renew"]
    VS_GROW_SAVINGS_S06["Pay Out"]
  end

  subgraph grp_Inquiry_to_Resolution["Inquiry to Resolution"]
    direction TB
    VS_RESOLVE_ISSUE_S01["Contact & Route"]
    VS_RESOLVE_ISSUE_S02["Identify & Authenticate"]
    VS_RESOLVE_ISSUE_S03["Classify Issue"]
    VS_RESOLVE_ISSUE_S04["Investigate"]
    VS_RESOLVE_ISSUE_S05["Decide & Adjust"]
    VS_RESOLVE_ISSUE_S06["Notify"]
    VS_RESOLVE_ISSUE_S07["Close & Learn"]
  end

  subgraph grp_Merchant_Signed_to_Settled["Merchant Signed to Settled"]
    direction TB
    VS_ENABLE_MERCHANT_S01["ISO Submits"]
    VS_ENABLE_MERCHANT_S02["Underwrite Merchant"]
    VS_ENABLE_MERCHANT_S03["Board & Sponsor"]
    VS_ENABLE_MERCHANT_S04["Accept & Settle"]
    VS_ENABLE_MERCHANT_S05["Monitor Exposure"]
    VS_ENABLE_MERCHANT_S06["Retain or Exit"]
  end

  subgraph grp_Prospect_to_Funded_Account["Prospect to Funded Account"]
    direction TB
    VS_ACQUIRE_CUSTOMER_S01["Target & Offer"]
    VS_ACQUIRE_CUSTOMER_S02["Apply"]
    VS_ACQUIRE_CUSTOMER_S03["Verify Identity"]
    VS_ACQUIRE_CUSTOMER_S04["Decide"]
    VS_ACQUIRE_CUSTOMER_S05["Open Account"]
    VS_ACQUIRE_CUSTOMER_S06["Fulfill Card"]
    VS_ACQUIRE_CUSTOMER_S07["Activate & First Use"]
  end

  subgraph grp_Transact_to_Statement["Transact to Statement"]
    direction TB
    VS_SERVICE_ACCOUNT_S01["Authorize"]
    VS_SERVICE_ACCOUNT_S02["Clear & Post"]
    VS_SERVICE_ACCOUNT_S03["Assess Interest & Fees"]
    VS_SERVICE_ACCOUNT_S04["Cut Cycle & Statement"]
    VS_SERVICE_ACCOUNT_S05["Deliver Statement"]
    VS_SERVICE_ACCOUNT_S06["Capture Payment"]
    VS_SERVICE_ACCOUNT_S07["Settle & Reconcile"]
  end


  classDef s_value_stream_stages__vs_acquire_customer fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_enable_merchant fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_finance_purchase fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_grow_savings fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_launch_product fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_onboard_client fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_recover_value fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_resolve_issue fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  classDef s_value_stream_stages__vs_service_account fill:#f3e8ff,stroke:#a855f7,color:#0f172a,stroke-width:1.4px;
  class VS_ACQUIRE_CUSTOMER_S01,VS_ACQUIRE_CUSTOMER_S02,VS_ACQUIRE_CUSTOMER_S03,VS_ACQUIRE_CUSTOMER_S04,VS_ACQUIRE_CUSTOMER_S05,VS_ACQUIRE_CUSTOMER_S06,VS_ACQUIRE_CUSTOMER_S07 s_value_stream_stages__vs_acquire_customer;
  class VS_ENABLE_MERCHANT_S01,VS_ENABLE_MERCHANT_S02,VS_ENABLE_MERCHANT_S03,VS_ENABLE_MERCHANT_S04,VS_ENABLE_MERCHANT_S05,VS_ENABLE_MERCHANT_S06 s_value_stream_stages__vs_enable_merchant;
  class VS_FINANCE_PURCHASE_S01,VS_FINANCE_PURCHASE_S02,VS_FINANCE_PURCHASE_S03,VS_FINANCE_PURCHASE_S04,VS_FINANCE_PURCHASE_S05,VS_FINANCE_PURCHASE_S06,VS_FINANCE_PURCHASE_S07 s_value_stream_stages__vs_finance_purchase;
  class VS_GROW_SAVINGS_S01,VS_GROW_SAVINGS_S02,VS_GROW_SAVINGS_S03,VS_GROW_SAVINGS_S04,VS_GROW_SAVINGS_S05,VS_GROW_SAVINGS_S06 s_value_stream_stages__vs_grow_savings;
  class VS_LAUNCH_PRODUCT_S01,VS_LAUNCH_PRODUCT_S02,VS_LAUNCH_PRODUCT_S03,VS_LAUNCH_PRODUCT_S04,VS_LAUNCH_PRODUCT_S05,VS_LAUNCH_PRODUCT_S06 s_value_stream_stages__vs_launch_product;
  class VS_ONBOARD_CLIENT_S01,VS_ONBOARD_CLIENT_S02,VS_ONBOARD_CLIENT_S03,VS_ONBOARD_CLIENT_S04,VS_ONBOARD_CLIENT_S05,VS_ONBOARD_CLIENT_S06,VS_ONBOARD_CLIENT_S07 s_value_stream_stages__vs_onboard_client;
  class VS_RECOVER_VALUE_S01,VS_RECOVER_VALUE_S02,VS_RECOVER_VALUE_S03,VS_RECOVER_VALUE_S04,VS_RECOVER_VALUE_S05,VS_RECOVER_VALUE_S06,VS_RECOVER_VALUE_S07 s_value_stream_stages__vs_recover_value;
  class VS_RESOLVE_ISSUE_S01,VS_RESOLVE_ISSUE_S02,VS_RESOLVE_ISSUE_S03,VS_RESOLVE_ISSUE_S04,VS_RESOLVE_ISSUE_S05,VS_RESOLVE_ISSUE_S06,VS_RESOLVE_ISSUE_S07 s_value_stream_stages__vs_resolve_issue;
  class VS_SERVICE_ACCOUNT_S01,VS_SERVICE_ACCOUNT_S02,VS_SERVICE_ACCOUNT_S03,VS_SERVICE_ACCOUNT_S04,VS_SERVICE_ACCOUNT_S05,VS_SERVICE_ACCOUNT_S06,VS_SERVICE_ACCOUNT_S07 s_value_stream_stages__vs_service_account;
  classDef boundary1 fill:#f3f5fb,stroke:#8f9bb5,color:#3b4a6b;
  class grp_Client_Opportunity_to_Live_Program,grp_Concept_to_Market,grp_Dealer_Purchase_to_Funded_Loan,grp_Delinquency_to_Recovery,grp_Deposit_Opened_to_Maturity,grp_Inquiry_to_Resolution,grp_Merchant_Signed_to_Settled,grp_Prospect_to_Funded_Account,grp_Transact_to_Statement boundary1;
```

The same view as the app draws it, written beside the Mermaid by `terrane render`:

![Value Streams](../svg/value-streams.svg)

**value stream id** is the boundary each node sits in.

60 entities, 0 relationships. Generated from the model; edit the model, not this file.

> No edges connected the selected entities.
