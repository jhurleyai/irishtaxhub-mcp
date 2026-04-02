# Sample Questions

Practical prompts you can use with any AI agent connected to the Irish Tax Hub MCP server. The agent figures out which tool to call based on your question — you just ask naturally.

## Tax Calculations

These trigger `calculate_tax` (and `get_calculator_schema` if the agent needs to look up the input fields first).

### Income Tax / PAYE

- "What tax would I pay on a salary of €75,000 as a single person?"
- "I'm married one income, earning €120k with a 5% pension contribution. What's my take-home?"
- "What gross salary do I need to take home €4,000 per month?"

### Tax Refunds

- "How much tax refund would I get if I earned €50k and paid €18k in tax?"
- "I'm moving to Ireland in June on a €90k salary — what are my tax-free earnings?"
- "I left Ireland in September — what refund am I due?"

### Rental Income

- "I have rental income of €24,000 with €8,000 in expenses — what tax do I owe?"
- "I rent out a property for €2,000/month. What's my tax bill as a single person earning €60k?"

### Self-Employed

- "I'm self-employed with turnover of €80k and €20k in expenses. What's my tax?"
- "Calculate tax for a sole trader earning €50k with €5k in capital allowances"

### Capital Gains Tax

- "Calculate CGT on a property I bought for €250k and sold for €400k"
- "I bought shares for €10k in 2020 and sold them for €25k — what CGT do I owe?"

### Share Options

- "I got 1,000 share options at €5, now worth €25 — what's the RTSO?"
- "I exercised share options and sold the shares — what's the CGT?"

### Pensions & AVCs

- "What's the max AVC I can contribute at age 45 earning €100k?"
- "Estimate my pension fund at retirement — I'm 30, retiring at 65, €500/month contributions"
- "How much will my pension be worth if I invest €1,000/month with 5% growth?"

### Mortgage

- "Can I afford a mortgage on €85k salary with €40k savings as a first-time buyer?"
- "What are the monthly repayments on a €350k mortgage over 30 years at 4%?"

### Redundancy

- "I'm being made redundant after 12 years, weekly pay €900 — what's taxable?"
- "Calculate tax on a redundancy payment of €50k after 8 years of service"

### Work From Home

- "I worked from home 200 days this year — what tax relief can I claim?"

### CAT (Gifts & Inheritances)

- "I'm inheriting €400k from my parent — what CAT do I owe?"
- "My aunt is gifting me €50k — what's the tax?"

### SARP

- "I'm relocating to Ireland on a €150k salary under SARP — what's my relief?"

### VAT

- "Calculate my VAT3 return figures"

## Tax Reference Data

### Tax Constants (`get_tax_constants`)

- "What are the current income tax bands for 2025?"
- "What's the USC rate for income over €70,044?"
- "Show me the PRSI rates"
- "What are the tax credits for a married couple?"

### Key Dates (`get_key_dates`)

- "When is the deadline to file my self-employed tax return?"
- "What are the key VAT dates this year?"
- "Show me all Revenue deadlines for October"
- "What PAYE dates should I be aware of?"

## Revenue Documents

### Search (`search_revenue_documents`)

- "Find the Revenue guidance on rent tax credit"
- "What does Revenue say about CGT principal private residence relief?"
- "Search for TDMs about PAYE credits"
- "Find Revenue guidance on remote working relief"

### Read Full Document (`get_revenue_document_text`)

- "Get the full text of the Revenue manual on share options"
- "Show me the TDM for rental income deductions"

### Categories (`list_revenue_document_categories`)

- "What categories of Revenue documents are available?"

## Recent Revenue Changes

### eBrief Changelog (`get_revenue_ebrief_changelog`)

- "What Revenue guidance has changed recently?"
- "Any new eBriefs this month?"
- "Show me recent updates to Revenue manuals"

## AI Summary

### Plain-English Tax Summary (`generate_net_income_summary`)

- "Calculate my tax on €80k and give me a plain-English summary"
- "Break down my take-home pay in simple terms — €95k salary, married, one income"

The agent will call `calculate_tax` first, then pass the result to `generate_net_income_summary` to produce a readable explanation.

## Calculator Stats

### Usage Statistics (`get_calculator_stats`)

- "How many people have used the mortgage calculator?"
- "Show me usage stats for the refund calculator"
