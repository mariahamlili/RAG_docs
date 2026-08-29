# Empty PDF OCR probe (CAI-018)

**Engine:** PyMuPDF `get_textpage_ocr` + Tesseract 5.x @ 200 DPI
**Runtime:** 223.0s for 34 PDFs

## Summary

| Status | Count | Meaning |
|---|---:|---|
| OCR_OK | 34 | Usable text recovered (≥50 tok or ≥200 chars) |
| OCR_WEAK | 0 | Some text, below threshold |
| OCR_GARBAGE | 0 | Mostly noise/symbols |
| OCR_EMPTY | 0 | Zero characters after OCR |
| OCR_ERROR | 0 | Exception during OCR |

## Per-file results

| # | File | Pages | Plain | OCR chars | OCR tokens | Status | Sample |
|---|---|---:|---:|---:|---:|---|---|
| 1 | [accc.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/better-regulation-of-ag-vet-chemicals/streamlining/public-consultation/accc.pdf) | 4 | 0 | 8498 | 1343 | OCR_OK | x ky: 3 ¢ RIEL AUSTRALIAN COMPETITION & CONSUMER COMMISSION 23 Marcus Clarke Street Canberra ACT 2601 GPO Box 3131 Conta |
| 2 | [accord.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/better-regulation-of-ag-vet-chemicals/streamlining/public-consultation/accord.pdf) | 4 | 0 | 10128 | 1464 | OCR_OK | F accord hygiene, cosmetic & specialty products industry Streamlining Regulation of Agricultural and Veterinary Chemical |
| 3 | [competitive-advantage.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/better-regulation-of-ag-vet-chemicals/streamlining/public-consultation/competitive-advantage.pdf) | 3 | 0 | 6027 | 967 | OCR_OK | Agvet Reform From: Mike Tichon <mike.tichon@competitive-advantage.com.au> Sent: Wednesday, 19 July 2017 2:08 PM To: Agve |
| 4 | [wa-farmers.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/better-regulation-of-ag-vet-chemicals/streamlining/public-consultation/wa-farmers.pdf) | 8 | 0 | 16628 | 2371 | OCR_OK | x ee,Koy, y! Australian Government “Reig? Department ofAgriculture and Water Resources Submission on Streamlining Regula |
| 5 | [accc.pdf](../pdf/source/agriculture.gov.au/agvet-chemicals/better-regulation-of-ag-vet-chemicals/streamlining/regulations-consultation/accc.pdf) | 4 | 0 | 9046 | 1413 | OCR_OK | i’ Be eh = A j AUSTRALIAN COMPETITION i & CONSUMER COMMISSION 23 Marcus Clarke Street Canberra ACT 2601 Our ref: PRJ1003 |
| 6 | [doc-01.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-01.pdf) | 8 | 0 | 25762 | 4150 | OCR_OK | : Page 1 . Current as at 20 May 2011 SENATE ESTIMATES — MAy 2011 / SUPPLEMENTARY BRIEF / / GENETICALLY MODIFIED CROPS AN |
| 7 | [doc-02.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-02.pdf) | 3 | 0 | 10374 | 1638 | OCR_OK | j ‘ Page 9 DIVISIONAL BRIEF~RESEARCH, INNOVATION & TRAINING i BIOTECHNOLOGY - 1 : / GM CANOLA IN AUSTRALIA AND MARKETING |
| 8 | [doc-03.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-03.pdf) | 5 | 0 | 13019 | 2160 | OCR_OK | / / Page 12 Updated: 30 September 2011 / Question Time Brief : GENETICALLY MODIFIED CROPS IN / AUSTRALIA . sl Current Is |
| 9 | [doc-04.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-04.pdf) | 4 | 0 | 9863 | 1634 | OCR_OK | / Page 17 Updated: 25 August 2011 Question Time Brief GENETICALLY MODIFIED CROPS IN AUSTRALIA / Current Issue Genetic mo |
| 10 | [doc-05.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-05.pdf) | 2 | 0 | 5229 | 862 | OCR_OK | Page 21 In-Confidence / Question Time Brief / / GENETICALLY MODIFIED WHEAT / i FIELD TRIALS / Current Issue: ¢ Greenpeac |
| 11 | [doc-06.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-06.pdf) | 2 | 0 | 5084 | 844 | OCR_OK | / Page 23 In-Confidence : Question Time Brief GENETICALLY MODIFIED WHEAT ! FIELD TRIALS / Current Issue: / ® Greenpeace  |
| 12 | [doc-07.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-07.pdf) | 6 | 0 | 8180 | 1392 | OCR_OK | Page 25 IN CONFIDENCE GM CROPS IN AUSTRALIA / QUESTION What is the benefit of genetically modified (GM) crops; and what  |
| 13 | [doc-08.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-08.pdf) | 3 | 0 | 6002 | 975 | OCR_OK | Page 31 / / GENETICALLY MODIFIED WHEAT AND SUGAR IN AUSTRALIA / / Policy position / The Government believes GM technolog |
| 14 | [doc-09.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-09.pdf) | 3 | 0 | 6390 | 1049 | OCR_OK | / Page 34 : Australian policies on genetically modified (GM) crops and food / « The national framework for management an |
| 15 | [doc-10.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-10.pdf) | 4 | 0 | 7140 | 1127 | OCR_OK | G-06 Pesos? Last Updated: 27 October 2010 / IN CONFIDENCE GENETICALLY MODIFIED CROPS IN AUSTRALIA QUESTION / ; What is t |
| 16 | [doc-11.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-11.pdf) | 4 | 0 | 5362 | 859 | OCR_OK | ' / Page 41 / G-07 Last Updated: 18 October 2010 / IN CONFIDENCE / GENETICALLY MODIFIED CROPS IN AUSTRALIA / QUESTION /  |
| 17 | [doc-12.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-12.pdf) | 4 | 0 | 7328 | 1166 | OCR_OK | / / Page 45 i / Updated: 4 Junely 2011 GENETICALLY MODIFIED CROPS IN AUSTRALIA / / Current Issue / e What measures will  |
| 18 | [doc-13.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-13.pdf) | 4 | 0 | 7198 | 1149 | OCR_OK | Page 49 / / Updated: 30244 June 2011 ! GENETICALLY MODIFIED CROPS IN AUSTRALIA Current Issue , e What measures will the  |
| 19 | [doc-14.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-14.pdf) | 4 | 0 | 6185 | 975 | OCR_OK | { Page 53 ; Updated: 5 May 2011 : GENETICALLY MODIFIED CROPS IN AUSTRALIA / / Current Issue 7 e What measures will the g |
| 20 | [doc-15.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-15.pdf) | 4 | 0 | 7244 | 1174 | OCR_OK | 1 Page 57 / Updated: 4 July 2011 / GENETICALLY MODIFIED CROPS IN AUSTRALIA / / Current Issue ' ¢ What is the government  |
| 21 | [doc-16.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-16.pdf) | 4 | 0 | 6204 | 984 | OCR_OK | Page 61 Updated: 4 February 2011 GENETICALLY MODIFIED CROPS IN AUSTRALIA / Current Issue « What measures will the govern |
| 22 | [doc-17.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-17.pdf) | 2 | 0 | 3913 | 610 | OCR_OK | / / Page 65 / Background brief-GM Wheat and GM Sugarcane in Australia ' GENETICALLY MODIFIED WHEAT AND SUGARCANE IN AUST |
| 23 | [doc-18.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-18.pdf) | 3 | 0 | 6223 | 1077 | OCR_OK | { Page 87 Brief current as at X February 2011 1 Key Estimates Brief ; GENETICALLY MODIFIED (GM) CROPS AND FOOD IN AUSTRA |
| 24 | [doc-19.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-19.pdf) | 2 | 0 | 6268 | 1043 | OCR_OK | Page 70 REVISED VERSION / BACK TO INDEX i Brief current as atX October 2011 / ! KEY ISSUE BRIEF <NUMBER> GENETICALLY MOD |
| 25 | [doc-20.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-20.pdf) | 1 | 0 | 1756 | 295 | OCR_OK | / / Page 72 . Other issues Post should be aware of: - On 14 July 2011 Greenpeace activists scaled a CSIRO trial site of  |
| 26 | [doc-21.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-21.pdf) | 3 | 0 | 8305 | 1343 | OCR_OK | Page 73 IN CONFIDENCE Meeting with Mr Jeremy Tager and SURKG@D) , Greenpeace 2:00pm, 3 November 2010 Hii 1. On 27 Octobe |
| 27 | [doc-22.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-22.pdf) | 2 | 0 | 4064 | 664 | OCR_OK | . / Page 76 / / Dear xxxxx / Thank you for your email/letter of xxxxxxxxx to the Minister for Health and Ageing, the Hon |
| 28 | [doc-23.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-23.pdf) | 7 | 0 | 23766 | 3792 | OCR_OK | / Page 78 i Current as at 18 February 2011 : SENATE ESTIMATES — FEBRUARY 2011 : SUPPLEMENTARY BRIEF GENETICALLY MODIFIED |
| 29 | [doc-24.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-24.pdf) | 6 | 0 | 18322 | 2942 | OCR_OK | / 1 Page 85 Current as at 7 October 2010 ; SENATE ESTIMATES — OCTOBER 2010 / SUPPLEMENTARY BRIEF GENETICALLY MODIFIED CR |
| 30 | [doc-25.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-25.pdf) | 8 | 0 | 28954 | 4687 | OCR_OK | Page 91 Current as at 27 September 2011 SENATE ESTIMATES ~ OCTOBER 2011 / SUPPLEMENTARY BRIEF GENETICALLY MODIFIED CROPS |
| 31 | [doc-26.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-26.pdf) | 1 | 0 | 2747 | 470 | OCR_OK | ! Page 99 / Keightley, Ryan / / From: Hodge, Leanne / Sent: Friday, 15 July 2011 2:17 PM \ To: Janiec Stefanie / Ce: Rya |
| 32 | [doc-27.pdf](../pdf/source/agriculture.gov.au/biotechnology/doc-27.pdf) | 3 | 0 | 3869 | 614 | OCR_OK | / Page 100 / COMMERCIAL-IN-CONFIDENCE Printed by ICED-DW02L - 04:13 PM Monday, 12 September 2011 1C37190L / Title: New C |
| 33 | [tamworth-walcha-rdr-plan.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/future-drought-fund/regional-drought-resilience-planning/tamworth-walcha-rdr-plan.pdf) | 60 | 0 | 217889 | 61620 | OCR_OK | M\™$}?M ES “SS eeEe Sn ee SSO GE SS OSgo= SEENoN =. << XxGOO,SSS eo SSS TAMWORTH REGIONAL COUNCIL SSEOS SS ER Ke es/ <7  |
| 34 | [rfcs-program-program-logic-infographic.pdf](../pdf/source/agriculture.gov.au/drought-and-farm-support/rural-financial-counselling-service/rfcs-program-program-logic-infographic.pdf) | 1 | 0 | 4890 | 716 | OCR_OK | * Lifeson. Australian Government e e e e e CONTEXT: Fiscal environment, climatic events, industry events (disease outbre |

Full JSON: `data/manifests/empty_extractions_ocr_probe.json`

