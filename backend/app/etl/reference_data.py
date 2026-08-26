"""External domain reference data — NOT observed in the Kaggle dataset.

The WHO ATC classification names below are a public, standard drug
classification (https://www.who.int/tools/atc-ddd-toolkit), included here
as annotation to make the 8 source columns interpretable. They are seeded
into dim_atc_class with source="external_who_atc_reference" so nothing in
the database can be mistaken for something the Kaggle CSVs themselves
report. See docs/01-data-dictionary.md for the same table."""

ATC_REFERENCE: dict[str, dict[str, str]] = {
    "M01AB": {
        "atc_name": "Antiinflammatory/antirheumatic products, non-steroids — acetic acid derivatives",
        "therapeutic_group": "Musculoskeletal system",
    },
    "M01AE": {
        "atc_name": "Antiinflammatory/antirheumatic products, non-steroids — propionic acid derivatives",
        "therapeutic_group": "Musculoskeletal system",
    },
    "N02BA": {
        "atc_name": "Other analgesics and antipyretics — salicylic acid derivatives",
        "therapeutic_group": "Nervous system",
    },
    "N02BE": {
        "atc_name": "Other analgesics and antipyretics — anilides",
        "therapeutic_group": "Nervous system",
    },
    "N05B": {
        "atc_name": "Psycholeptics — anxiolytics",
        "therapeutic_group": "Nervous system",
    },
    "N05C": {
        "atc_name": "Psycholeptics — hypnotics and sedatives",
        "therapeutic_group": "Nervous system",
    },
    "R03": {
        "atc_name": "Drugs for obstructive airway diseases",
        "therapeutic_group": "Respiratory system",
    },
    "R06": {
        "atc_name": "Antihistamines for systemic use",
        "therapeutic_group": "Respiratory system",
    },
}
