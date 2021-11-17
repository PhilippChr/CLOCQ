Template that indicates expected format of benchmarks for evaluation or inference.  
Remember to remove the comments before using this JSON-template.  
The file [benchmark_format.json](benchmark_format.json) has a valid format for usage.

```
    {   
        // dev split (used by --dev argument)
        "dev": [
            // List of dictionaries; one for each question
            {   
                // Natural language question
                "question": "Who played Arya in Game of Thrones?",
                // List of answers, given as Wikidata IDs
                "answers": [
                    // Wikidata ID without URL
                    "Q234363"
                ],
                // Any other data can be stored, and will be kept in the output .jsonl
                "any": ["other", "key"]
            },
            {
                "question": "Creator of Game of Thrones?",
                "answers": [
                    // Question with multiple answers
                    "Q1151388",
                    "Q503997"
                ]
            }
        ],
        // test split (used by --test argument)
        "test": [
            {
                "question": "What year was the Wizard of Oz released?", 
                "answers": [
                    // Literals (years, timestamps, yes/no,...) are given directly
                    "1939"
                ]
            }
        ]
    }
```